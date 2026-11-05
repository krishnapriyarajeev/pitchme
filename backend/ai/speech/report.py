"""Speech report: fluency and articulation turned into findings.

Not every number becomes a finding. One short pause or one unclear word is
normal speech. Only a pattern a listener would notice is reported: a pace
outside the comfortable range, a high filler rate, a run of hesitations, or
a clarity score below the bar.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby

from ai.core.llm import LLMClient
from ai.core.transcript import Transcript, Word
from ai.core.types import Finding, Severity, TimestampedNote

from .articulation import ArticulationReport, score_articulation
from .fluency import FluencyReport, Pause, WpmWindow, score_fluency

PIPELINE = "speech"

# A comfortable pace for a prepared talk or a sales call.
COMFORTABLE_WPM_RANGE = (110, 170)
# This far outside the range, pace is a medium problem, not a low one.
PACE_MEDIUM_MARGIN_WPM = 30

# Fillers per minute above which they distract. A rate, so a long talk is
# not punished for having more time to collect them.
FILLER_PER_MIN_THRESHOLD = 6.0

# This many hesitation pauses in a row reads as halting.
HESITATION_RUN_THRESHOLD = 3

# Below this clarity score, articulation is reported.
CLARITY_SCORE_THRESHOLD = 0.9

# Longest quote attached to a finding, in words.
QUOTE_MAX_WORDS = 25


@dataclass(frozen=True)
class SpeechReport:
    fluency: FluencyReport
    articulation: ArticulationReport
    findings: tuple[Finding, ...]


def quote_between(words: tuple[Word, ...], start_ms: int, end_ms: int) -> str:
    """What was said between two moments, cut to QUOTE_MAX_WORDS. A word
    that ends or starts exactly on a boundary is included, so a pause is
    quoted with the words on both sides of it."""
    spoken = [w.text for w in words if w.end_ms >= start_ms and w.start_ms <= end_ms]
    if len(spoken) > QUOTE_MAX_WORDS:
        spoken = [*spoken[:QUOTE_MAX_WORDS], "..."]
    return " ".join(spoken)


def _pace_direction(window: WpmWindow) -> str | None:
    low, high = COMFORTABLE_WPM_RANGE
    if window.wpm > high:
        return "pace_too_fast"
    if window.wpm < low:
        return "pace_too_slow"
    return None


def _pace_findings(fluency: FluencyReport, words: tuple[Word, ...]) -> list[Finding]:
    """One finding per stretch of overlapping windows that are all too fast
    or all too slow, instead of one per window."""
    low, high = COMFORTABLE_WPM_RANGE
    findings = []
    for category, group in groupby(fluency.wpm_windows, key=_pace_direction):
        if category is None:
            continue
        run = list(group)
        fast = category == "pace_too_fast"
        worst = max(run, key=lambda w: w.wpm) if fast else min(run, key=lambda w: w.wpm)
        margin = worst.wpm - high if fast else low - worst.wpm
        start, end = run[0].t_start_ms, run[-1].t_end_ms
        findings.append(
            Finding(
                pipeline=PIPELINE,
                category=category,
                severity=Severity.MEDIUM if margin >= PACE_MEDIUM_MARGIN_WPM else Severity.LOW,
                summary=f"Pace reached {worst.wpm:.0f} wpm, outside the comfortable "
                f"{low}-{high} wpm range.",
                note=TimestampedNote(start, end, quote_between(words, start, end)),
                details={"wpm": worst.wpm, "windows": len(run)},
            )
        )
    return findings


def _filler_finding(fluency: FluencyReport) -> Finding | None:
    if fluency.filler_per_min < FILLER_PER_MIN_THRESHOLD or not fluency.filler_counts:
        return None
    top = fluency.filler_counts[0]
    return Finding(
        pipeline=PIPELINE,
        category="frequent_fillers",
        severity=Severity.MEDIUM,
        summary=f"Filler words came {fluency.filler_per_min:.1f} times a minute; "
        f"the most common was {top.word!r} ({top.count} times).",
        details={
            "filler_per_min": fluency.filler_per_min,
            "filler_counts": {f.word: f.count for f in fluency.filler_counts},
        },
    )


def _hesitation_findings(fluency: FluencyReport, words: tuple[Word, ...]) -> list[Finding]:
    """One finding per run of hesitations with no deliberate pause between."""
    findings = []
    for is_hesitation, group in groupby(fluency.pauses, key=lambda p: p.is_hesitation):
        run: list[Pause] = list(group)
        if not is_hesitation or len(run) < HESITATION_RUN_THRESHOLD:
            continue
        start, end = run[0].start_ms, run[-1].end_ms
        findings.append(
            Finding(
                pipeline=PIPELINE,
                category="hesitation_run",
                severity=Severity.MEDIUM,
                summary=f"{len(run)} hesitation pauses in a row.",
                note=TimestampedNote(start, end, quote_between(words, start, end)),
                details={
                    "pause_count": len(run),
                    "total_pause_ms": sum(p.duration_ms for p in run),
                },
            )
        )
    return findings


def _articulation_finding(articulation: ArticulationReport) -> Finding | None:
    if articulation.words_checked == 0 or articulation.clarity_score >= CLARITY_SCORE_THRESHOLD:
        return None
    flags = articulation.flags
    rushed = sum(1 for f in flags if f.co_occurring_rate_spike)
    summary = (
        f"{articulation.unclear_words} of {articulation.words_checked} words were unclear "
        f"(clarity {articulation.clarity_score:.2f})."
    )
    if rushed * 2 >= len(flags):
        summary += " Most came while rushing, so slowing down should help."
    worst = min(flags, key=lambda f: f.logprob)
    return Finding(
        pipeline=PIPELINE,
        category="unclear_articulation",
        severity=Severity.MEDIUM,
        summary=summary,
        note=TimestampedNote(worst.t_start_ms, worst.t_end_ms, worst.text),
        details={
            "clarity_score": articulation.clarity_score,
            "unclear_words": articulation.unclear_words,
            "rushed_flags": rushed,
            "examples": [
                {"text": f.text, "t_start_ms": f.t_start_ms, "t_end_ms": f.t_end_ms}
                for f in sorted(flags, key=lambda f: f.logprob)[:5]
            ],
        },
    )


def score_speech(transcript: Transcript, llm: LLMClient | None = None) -> SpeechReport:
    """Run fluency and articulation and turn them into findings, most severe
    first, in time order within a severity."""
    fluency = score_fluency(transcript, llm)
    articulation = score_articulation(transcript)
    words = transcript.words

    findings = _pace_findings(fluency, words)
    findings.extend(_hesitation_findings(fluency, words))
    findings.extend(f for f in (_filler_finding(fluency), _articulation_finding(articulation)) if f)
    findings.sort(key=lambda f: (-f.severity.rank, f.note.t_start_ms if f.note else 0))

    return SpeechReport(fluency=fluency, articulation=articulation, findings=tuple(findings))
