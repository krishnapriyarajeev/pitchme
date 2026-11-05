import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from ai.analysis import pipeline
from ai.analysis.pipeline import AnalysisError, AnalysisRequest, run_analysis
from ai.core.llm import LLMClient, LLMError
from ai.core.transcript import Segment, Transcript, Word
from ai.core.types import Finding, Severity
from ai.rehearsal.transcript import CallTurn
from tests.ai.voice_cloning.fakes import FakeVoiceClient

pytest.importorskip("parselmouth", reason="needs the voice extra")
pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

BUYER_1 = "Yes, who is this and what do you want?"
SELLER_1 = "Hi Jo it is Sam from PitchMe and I wanted to talk about payroll"
BUYER_2 = "We already pay too much for software, what does it cost?"
SELLER_2 = "Um it depends on a lot of things really"

TURNS = (
    CallTurn("buyer", BUYER_1, 0, 2000),
    CallTurn("seller", SELLER_1, 2500, 6000),
    CallTurn("buyer", BUYER_2, 6500, 9000),
    CallTurn("seller", SELLER_2, 9500, 12000),
)


def spoken(*lines: str) -> Transcript:
    """What Whisper hears on the recording: one word every 250 ms."""
    segments, t = [], 0
    for line in lines:
        words = []
        for text in line.split():
            words.append(Word(text, t, t + 200))
            t += 250
        segments.append(Segment(line, words[0].start_ms, words[-1].end_ms, tuple(words)))
        t += 500
    return Transcript(tuple(segments))


class FakeTranscriber:
    def __init__(self, transcript=None, error=None):
        self.transcript = transcript or spoken(BUYER_1, SELLER_1, BUYER_2, SELLER_2)
        self.error = error

    def transcribe(self, path):
        if self.error:
            raise self.error
        return self.transcript


class RoutingLLM(LLMClient):
    """Answers each pipeline's prompt by the shape of its schema."""

    def __init__(self, fail_content=False):
        self.fail_content = fail_content
        self.asked = []

    def complete(self, prompt, *, system=None):
        raise AssertionError("only JSON replies are used")

    def complete_json(self, prompt, *, schema, system=None):
        keys = set(schema["properties"])
        self.asked.append(keys)
        if "exchanges" in keys:
            if self.fail_content:
                raise LLMError("judge down")
            return {
                "score": 55,
                "summary": "Price was dodged.",
                "exchanges": [
                    {"customer_quote": BUYER_2, "agent_quote": SELLER_2, "handled_well": False,
                     "category": "dodged", "reasoning": "No number.", "reference_evidence": ""},
                    {"customer_quote": BUYER_1, "agent_quote": SELLER_1, "handled_well": True,
                     "category": "handled", "reasoning": "Clear intro.", "reference_evidence": ""},
                ],
            }  # fmt: skip
        if "responses" in keys:
            return {
                "responses": [
                    {"exchange_id": "ex-0", "stronger_response": "It is a flat fee per seat.",
                     "citation": "", "change_summary": "Gave a straight answer."}
                ]
            }  # fmt: skip
        if "fillers" in keys:
            return {"fillers": [{"word": "um", "count": 1}], "summary": "One um."}
        raise AssertionError(f"unexpected schema {keys}")


@pytest.fixture(scope="module")
def recording(tmp_path_factory):
    path = tmp_path_factory.mktemp("call") / "call.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "sine=frequency=180:duration=14", "-c:a", "aac", str(path)],
        check=True,
    )  # fmt: skip
    return path


class Saved:
    def __init__(self):
        self.audio, self.video = [], []

    def save_audio(self, index, data):
        self.audio.append((index, data[:4]))
        return f"corrected-{index}.wav"

    def save_video(self, path):
        self.video.append(path.name)
        return "annotated.mp4"


def run(request, saved=None, **kwargs):
    saved = saved or Saved()
    stages = []
    kwargs.setdefault("llm", RoutingLLM())
    kwargs.setdefault("transcriber", FakeTranscriber())
    kwargs.setdefault("voice_client", FakeVoiceClient())
    result = run_analysis(
        request, save_audio=saved.save_audio, save_video=saved.save_video,
        on_stage=stages.append, **kwargs,
    )  # fmt: skip
    return result, stages, saved


def test_audio_call_scores_content_speech_and_voice(recording):
    result, stages, saved = run(
        AnalysisRequest(TURNS, recording=recording, voice_id="v1", mode="audio")
    )
    assert stages == ["transcribing", "analyzing", "finishing"]
    scores = {d.name: d.score for d in result.dimensions}
    assert scores["content"] == 55
    assert scores["speech"] is not None and scores["voice"] is not None
    assert scores["vision"] is None
    assert result.dimensions[-1].skipped == "Audio-only analysis was asked for."
    assert result.overall_score is not None
    assert (result.questions, result.handled) == (2, 1)
    assert result.strengths and result.prep_list
    (answer,) = result.corrected_answers
    assert answer.stronger == "It is a flat fee per seat." and answer.audio_key == "corrected-0.wav"
    assert saved.audio == [(0, b"RIFF")]
    assert result.notes == []
    # Everything lands in the database as JSON.
    data = json.loads(json.dumps(result.to_dict()))
    assert set(data["metrics"]) == {"speech", "voice"}
    assert data["dimensions"][0]["name"] == "content"


def test_speech_hears_only_the_seller(recording):
    llm = RoutingLLM()
    run(AnalysisRequest(TURNS, recording=recording, mode="audio"), llm=llm)
    # The filler prompt carries the seller's words, not the buyer's.
    assert any("fillers" in keys for keys in llm.asked)


def test_seller_only_times_point_back_at_the_recording(recording):
    result, _, _ = run(AnalysisRequest(TURNS, recording=recording, mode="audio"))
    first = result.metrics["speech"]["fluency"]["wpm_windows"][0]
    # The cut audio starts where the buyer's first line ends, 2.2 s in.
    assert first["t_start_ms"] == 2200
    voice_windows = result.metrics["voice"]["pitch"]["windows"]
    assert voice_windows[0]["t_start_s"] == 2.2


def test_without_a_recording_only_the_transcript_is_judged():
    result, stages, _ = run(AnalysisRequest(TURNS, voice_id="v1"))
    assert stages == ["analyzing", "finishing"]
    by_name = {d.name: d for d in result.dimensions}
    assert by_name["content"].score == 55
    assert by_name["speech"].skipped == "No recording to listen to."
    assert by_name["vision"].skipped == "No video to watch."
    assert result.notes == ["This call was not recorded, so only the transcript was judged."]
    assert result.overall_score == 55


def test_unreadable_recording_falls_back_to_the_transcript(recording):
    result, _, _ = run(
        AnalysisRequest(TURNS, recording=recording, mode="audio"),
        transcriber=FakeTranscriber(error=RuntimeError("whisper down")),
    )
    assert "The recording could not be read, so only the transcript was judged." in result.notes
    assert {d.name: d.score for d in result.dimensions}["content"] == 55


def test_no_clone_means_text_answers_and_a_note():
    result, _, saved = run(AnalysisRequest(TURNS))
    assert result.corrected_answers[0].audio_key is None
    assert saved.audio == []
    assert (
        result.notes[-1] == "Record a voice sample to hear the stronger answers in your own voice."
    )


def test_failed_speech_synthesis_keeps_the_text(monkeypatch):
    class BrokenVoice(FakeVoiceClient):
        def synthesize(self, *args):
            raise RuntimeError("402")

    result, _, _ = run(AnalysisRequest(TURNS, voice_id="v1"), voice_client=BrokenVoice())
    assert result.corrected_answers[0].audio_key is None
    assert "could not be spoken" in result.notes[-1]


def test_content_failure_skips_content_but_keeps_delivery(recording):
    result, _, _ = run(
        AnalysisRequest(TURNS, recording=recording, mode="audio"), llm=RoutingLLM(fail_content=True)
    )
    by_name = {d.name: d for d in result.dimensions}
    assert by_name["content"].score is None
    assert by_name["voice"].score is not None
    assert result.corrected_answers == []
    assert result.summary == pipeline.SKIP_REASONS["content"]


def test_nothing_said_is_an_error():
    with pytest.raises(AnalysisError):
        run(AnalysisRequest(()))


def test_video_adds_body_language_and_the_annotated_video(recording, monkeypatch):
    import ai.vision

    vision = SimpleNamespace(
        findings=(Finding("vision", "eye_contact", Severity.MEDIUM, "Looked away a lot."),),
        frames=(),
        movement=SimpleNamespace(movement_level="normal"),
        mode="qa",
    )
    monkeypatch.setattr(pipeline, "_vision", lambda path: vision)
    rendered = {}

    def fake_render(video, frames, output, *, voice, movement_level):
        rendered.update(voice=voice, movement=movement_level)
        output.write_bytes(b"mp4")
        return output

    monkeypatch.setattr(ai.vision, "render_annotated_video", fake_render)
    result, _, saved = run(AnalysisRequest(TURNS, recording=recording))
    by_name = {d.name: d for d in result.dimensions}
    assert by_name["vision"].score == 88
    assert by_name["vision"].summary == "Looked away a lot."
    assert result.annotated_video_key == "annotated.mp4" and saved.video == ["annotated.mp4"]
    assert rendered["voice"] is not None and rendered["movement"] == "normal"
    assert result.findings[0].severity.rank >= result.findings[-1].severity.rank


def test_failed_render_is_a_note(recording, monkeypatch):
    import ai.vision

    vision = SimpleNamespace(findings=(), frames=(), movement=SimpleNamespace(movement_level="x"))
    monkeypatch.setattr(pipeline, "_vision", lambda path: vision)

    def broken(*args, **kwargs):
        raise RuntimeError("ffmpeg")

    monkeypatch.setattr(ai.vision, "render_annotated_video", broken)
    result, _, _ = run(AnalysisRequest(TURNS, recording=recording))
    assert result.annotated_video_key is None
    assert "The annotated video could not be made for this call." in result.notes


def test_vision_failure_is_skipped_with_a_reason(recording, monkeypatch):
    def broken(path):
        raise RuntimeError("no models")

    monkeypatch.setattr(pipeline, "_vision", broken)
    result, _, _ = run(AnalysisRequest(TURNS, recording=recording))
    assert {d.name: d.skipped for d in result.dimensions}["vision"] == pipeline.SKIP_REASONS[
        "vision"
    ]


def test_a_call_without_questions_does_not_score_content():
    class NoQuestions(RoutingLLM):
        def complete_json(self, prompt, *, schema, system=None):
            if "exchanges" in schema["properties"]:
                return {"score": 100, "summary": "Nothing was asked.", "exchanges": []}
            return super().complete_json(prompt, schema=schema, system=system)

    result, _, _ = run(AnalysisRequest(TURNS), llm=NoQuestions())
    content = result.dimensions[0]
    assert (content.score, content.skipped) == (None, pipeline.NO_QUESTIONS)
    assert result.overall_score is None
    assert result.questions == 0 and result.corrected_answers == []
