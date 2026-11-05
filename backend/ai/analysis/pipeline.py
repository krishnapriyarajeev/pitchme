"""Analyse one finished rehearsal call.

1. Transcribe the recording and find the seller in it (separate.py).
2. In parallel: judge the content and rewrite weak answers; score speech
   and voice on the seller alone; score body language on the video.
3. Speak the stronger answers in the user's cloned voice, and render the
   annotated video.

A part that fails is skipped with a plain reason and the rest still
counts; the first version dropped delivery without saying so. Files are
handed to `save_audio` and `save_video`, which return storage keys, so
this module never touches storage itself.
"""

from __future__ import annotations

import dataclasses
import logging
import tempfile
import wave
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ai.content.reference import ReferenceDocument
from ai.content.report import ContentReport, Line, lines_from_turns, score_content
from ai.core.llm import LLMClient
from ai.core.transcript import Transcript
from ai.core.types import Finding, Severity, TimestampedNote
from ai.diarize.align import tag_speakers
from ai.diarize.base import DiarizedSegment
from ai.diarize.filter_speaker import filter_transcript, kept_ranges, original_time
from ai.rehearsal.transcript import CallTurn, to_lines
from ai.transcribe.base import TranscribeClient
from ai.voice_cloning.answers import AnswerCorrection, correct_answers
from ai.voice_cloning.base import VoiceCloneClient

from . import scoring
from .scoring import DimensionScore
from .separate import SELLER, separate_speakers
from .serialize import jsonable, remap_times

log = logging.getLogger(__name__)

Mode = Literal["audio", "audio_video"]
Stage = Literal["transcribing", "analyzing", "finishing"]

# The debrief's short list of what to work on first.
PREP_LIST_SIZE = 3


@dataclass(frozen=True)
class AnalysisRequest:
    turns: tuple[CallTurn, ...]
    # The call recording on disk; None when it was not recorded.
    recording: Path | None = None
    # The user's playbook, when they uploaded one.
    reference: ReferenceDocument | None = None
    voice_id: str | None = None
    mode: Mode = "audio_video"


@dataclass(frozen=True)
class CorrectedAnswer:
    question: str
    original: str
    stronger: str
    change: str
    citation: str
    # False when the rewrite has a number from nowhere; it is not spoken.
    verified: bool
    unsupported_numbers: tuple[str, ...]
    t_start_ms: int | None
    audio_key: str | None = None


@dataclass
class AnalysisResult:
    overall_score: int | None
    dimensions: list[DimensionScore]
    summary: str
    findings: list[Finding]
    strengths: list[str]
    prep_list: list[str]
    corrected_answers: list[CorrectedAnswer]
    questions: int
    handled: int
    metrics: dict[str, Any] = field(default_factory=dict)
    annotated_video_key: str | None = None
    # Things the user should know about this analysis, in plain words.
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "strengths": self.strengths,
            "prep_list": self.prep_list,
            "corrected_answers": [jsonable(c) for c in self.corrected_answers],
            "questions": self.questions,
            "handled": self.handled,
            "metrics": self.metrics,
            "annotated_video_key": self.annotated_video_key,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class _Seller:
    """The seller's part of the recording."""

    wav: Path
    transcript: Transcript
    segments: tuple[DiarizedSegment, ...]
    lines: tuple[Line, ...]
    # The seller's stretches of the recording; maps cut-audio times back.
    ranges: list[tuple[int, int]]


class AnalysisError(RuntimeError):
    """Nothing could be analysed."""


def _shift_note(
    note: TimestampedNote | None, ranges: list[tuple[int, int]]
) -> TimestampedNote | None:
    if note is None:
        return None
    return dataclasses.replace(
        note,
        t_start_ms=original_time(note.t_start_ms, ranges),
        t_end_ms=original_time(note.t_end_ms, ranges),
    )


def _on_recording_timeline(
    findings: Sequence[Finding], ranges: list[tuple[int, int]]
) -> list[Finding]:
    """Findings from the seller-only audio, pointing at the full recording."""
    return [dataclasses.replace(f, note=_shift_note(f.note, ranges)) for f in findings]


def _prepare(
    recording: Path, turns: Sequence[CallTurn], workdir: Path, transcriber: TranscribeClient
) -> _Seller | None:
    from ai.utils.audio import extract_audio

    wav = Path(extract_audio(recording, workdir / "call.wav"))
    transcript = transcriber.transcribe(wav)
    if transcript.is_empty:
        return None
    segments = separate_speakers(transcript, [t.text for t in turns if t.role == "buyer"])
    tagged = tag_speakers(transcript, segments)
    with wave.open(str(wav)) as audio:
        total_ms = round(audio.getnframes() / audio.getframerate() * 1000)
    return _Seller(
        wav=wav,
        transcript=filter_transcript(tagged, SELLER, segments),
        segments=segments,
        lines=lines_from_turns(tagged.turns(), agent_speaker=SELLER),
        ranges=kept_ranges(segments, SELLER, total_ms),
    )


def _content(lines: Sequence[Line], reference: ReferenceDocument | None, llm: LLMClient | None):
    report = score_content(lines, reference, llm)
    corrections = correct_answers(report.needs_work, llm) if report.needs_work else ()
    return report, corrections


def _speech(seller: _Seller, llm: LLMClient | None):
    from ai.speech import score_speech

    report = score_speech(seller.transcript, llm)
    return report, _on_recording_timeline(report.findings, seller.ranges)


def _voice(seller: _Seller):
    from ai.diarize.filter_speaker import filter_audio
    from ai.voice import analyze_voice, load_audio

    signal = filter_audio(load_audio(seller.wav), seller.segments, SELLER)
    report = analyze_voice(signal, "qa")
    return report, _on_recording_timeline(report.findings, seller.ranges)


def _vision(recording: Path):
    from ai.vision import score_vision

    return score_vision(recording, mode="qa")


NO_QUESTIONS = "The buyer asked no questions, so there were no answers to judge."

SKIP_REASONS = {
    "content": "The content check failed. Run the analysis again to retry it.",
    "speech": "Speech could not be scored for this call.",
    "voice": "Voice could not be scored for this call.",
    "vision": "Body language could not be scored for this call.",
}


def run_analysis(
    request: AnalysisRequest,
    *,
    save_audio: Callable[[int, bytes], str],
    save_video: Callable[[Path], str],
    on_stage: Callable[[Stage], None] = lambda stage: None,
    llm: LLMClient | None = None,
    transcriber: TranscribeClient | None = None,
    voice_client: VoiceCloneClient | None = None,
) -> AnalysisResult:
    notes: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pitchme-analysis-") as tmp:
        seller: _Seller | None = None
        if request.recording is not None:
            on_stage("transcribing")
            from ai.providers import get_transcribe_client

            try:
                seller = _prepare(
                    request.recording,
                    request.turns,
                    Path(tmp),
                    transcriber or get_transcribe_client(),
                )
            except Exception:
                log.exception("Could not transcribe the recording")
            if seller is None:
                notes.append("The recording could not be read, so only the transcript was judged.")
        else:
            notes.append("This call was not recorded, so only the transcript was judged.")

        lines = seller.lines if seller else to_lines(request.turns)
        if not lines:
            raise AnalysisError("The call has no speech to analyse.")

        on_stage("analyzing")
        jobs: dict[str, Callable[[], Any]] = {
            "content": lambda: _content(lines, request.reference, llm)
        }
        if seller:
            jobs["speech"] = lambda: _speech(seller, llm)
            jobs["voice"] = lambda: _voice(seller)
        if request.recording is not None and request.mode == "audio_video":
            jobs["vision"] = lambda: _vision(request.recording)
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {name: pool.submit(job) for name, job in jobs.items()}
        done: dict[str, Any] = {}
        for name, future in futures.items():
            try:
                done[name] = future.result()
            except Exception:
                log.exception("The %s part of the analysis failed", name)

        on_stage("finishing")
        return _assemble(
            request, seller, done, notes, Path(tmp), save_audio, save_video, voice_client
        )


def _assemble(
    request: AnalysisRequest,
    seller: _Seller | None,
    done: dict[str, Any],
    notes: list[str],
    workdir: Path,
    save_audio: Callable[[int, bytes], str],
    save_video: Callable[[Path], str],
    voice_client: VoiceCloneClient | None,
) -> AnalysisResult:
    dimensions: list[DimensionScore] = []
    findings: list[Finding] = []
    metrics: dict[str, Any] = {}

    content: ContentReport | None = None
    corrections: tuple[AnswerCorrection, ...] = ()
    if "content" in done:
        content, corrections = done["content"]
        if any(f.category != "no_questions" for f in content.findings):
            dimensions.append(scoring.content_score(content.score, content.summary))
        else:
            # The judge still returns a score, often 100, for a call with
            # nothing to judge; counting it would lift the overall score.
            dimensions.append(scoring.skipped("content", NO_QUESTIONS))
        findings.extend(content.findings)
    else:
        dimensions.append(scoring.skipped("content", SKIP_REASONS["content"]))

    for name in ("speech", "voice"):
        if name in done:
            report, shifted = done[name]
            dimensions.append(scoring.from_findings(name, shifted))
            findings.extend(shifted)
            metrics[name] = remap_times(jsonable(report, drop={"findings"}), seller.ranges)
        elif seller is None:
            dimensions.append(scoring.skipped(name, "No recording to listen to."))
        else:
            dimensions.append(scoring.skipped(name, SKIP_REASONS[name]))

    vision_report = done.get("vision")
    if vision_report is not None:
        dimensions.append(scoring.from_findings("vision", vision_report.findings))
        findings.extend(vision_report.findings)
        metrics["vision"] = jsonable(vision_report, drop={"findings", "frames"})
    elif request.mode == "audio":
        dimensions.append(scoring.skipped("vision", "Audio-only analysis was asked for."))
    elif request.recording is None:
        dimensions.append(scoring.skipped("vision", "No video to watch."))
    else:
        dimensions.append(scoring.skipped("vision", SKIP_REASONS["vision"]))

    findings.sort(key=lambda f: -f.severity.rank)
    answers = _speak(corrections, request.voice_id, voice_client, save_audio, notes)
    video_key = (
        _annotate(
            request.recording, vision_report, done.get("voice"), seller, workdir, save_video, notes
        )
        if vision_report is not None and request.recording is not None
        else None
    )

    content_findings = content.findings if content else ()
    questions = [f for f in content_findings if f.category != "no_questions"]
    return AnalysisResult(
        overall_score=scoring.overall(dimensions),
        dimensions=dimensions,
        summary=content.summary if content else SKIP_REASONS["content"],
        findings=findings,
        strengths=[f.summary for f in questions if f.category == "handled"],
        prep_list=[f.summary for f in findings if f.severity.rank >= Severity.MEDIUM.rank][
            :PREP_LIST_SIZE
        ],
        corrected_answers=answers,
        questions=len(questions),
        handled=sum(f.category == "handled" for f in questions),
        metrics=metrics,
        annotated_video_key=video_key,
        notes=notes,
    )


def _speak(
    corrections: Sequence[AnswerCorrection],
    voice_id: str | None,
    voice_client: VoiceCloneClient | None,
    save_audio: Callable[[int, bytes], str],
    notes: list[str],
) -> list[CorrectedAnswer]:
    """Stronger answers, spoken in the user's voice when there is a clone.
    Without one they stay text: the first version spoke them in a stock
    voice, which is not the user's."""
    answers = [
        CorrectedAnswer(
            question=c.customer_quote,
            original=c.original_answer,
            stronger=c.stronger_response,
            change=c.change_summary,
            citation=c.citation,
            verified=c.verified,
            unsupported_numbers=c.unsupported_numbers,
            t_start_ms=c.t_start_ms,
        )
        for c in corrections
    ]
    if not answers:
        return answers
    if not voice_id:
        notes.append("Record a voice sample to hear the stronger answers in your own voice.")
        return answers
    from ai.voice_cloning.playback import speak_answers

    try:
        clips = speak_answers(corrections, voice_id, voice_client)
    except Exception:
        log.exception("Could not speak the stronger answers")
        notes.append("The stronger answers could not be spoken this time; the text is below.")
        return answers
    by_answer = {id(clip.correction): clip for clip in clips}
    out = []
    for index, (answer, correction) in enumerate(zip(answers, corrections, strict=True)):
        clip = by_answer.get(id(correction))
        key = save_audio(index, clip.audio) if clip else None
        out.append(dataclasses.replace(answer, audio_key=key))
    return out


def _annotate(
    recording: Path,
    vision_report: Any,
    voice_done: Any,
    seller: _Seller | None,
    workdir: Path,
    save_video: Callable[[Path], str],
    notes: list[str],
) -> str | None:
    from ai.vision import render_annotated_video, voice_timeline

    timeline = None
    if voice_done is not None and seller is not None:
        timeline = _timeline_on_recording(voice_timeline(voice_done[0]), seller.ranges)
    try:
        path = render_annotated_video(
            recording,
            vision_report.frames,
            workdir / "annotated.mp4",
            voice=timeline,
            movement_level=vision_report.movement.movement_level,
        )
        return save_video(path)
    except Exception:
        log.exception("Could not render the annotated video")
        notes.append("The annotated video could not be made for this call.")
        return None


def _timeline_on_recording(timeline: Any, ranges: list[tuple[int, int]]) -> Any:
    def at(seconds: float) -> float:
        return original_time(round(seconds * 1000), ranges) / 1000

    windows = tuple(
        dataclasses.replace(w, t_start_s=at(w.t_start_s), t_end_s=at(w.t_end_s))
        for w in timeline.windows
    )
    return dataclasses.replace(timeline, windows=windows)
