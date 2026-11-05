"""Voice report: every acoustic measure turned into findings.

No LLM call; every finding comes from a threshold. Thresholds depend on the
mode: a prepared presentation is held to a tighter standard than answers to
questions, where a shakier voice and a less even pace are normal.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeVar

from ai.core.types import Finding, Severity, TimestampedNote
from ai.utils.media import MediaStore, local_media

from .loudness import LoudnessReport, analyze_loudness
from .pitch import IntonationReport, PitchReport, PitchWindow, analyze_intonation, analyze_pitch
from .quality import NervousnessReport, analyze_nervousness
from .rate import RateWindow, SpeakingRateReport, analyze_rate
from .signal import MIN_DURATION_S, AudioSignal, load_audio

PIPELINE = "voice"
AnalysisMode = Literal["presentation", "qa"]

# Above this share of flat 2 second stretches the voice sounds monotone,
# whatever the overall range.
MONOTONE_FRACTION_THRESHOLD = 0.85
# A window this many times above or below the speaker's own mean pitch.
PITCH_WINDOW_DEVIATION_FACTOR = 1.5
# A window this many dB below the speaker's own mean loudness.
LOUDNESS_DROP_DB = 8.0
# A window's jitter this far above the speaker's own level is a spike.
JITTER_SPIKE_FACTOR = 1.3
# Window findings of one kind are capped, worst first.
MAX_WINDOW_FINDINGS = 3


class _Window(Protocol):
    t_start_s: float
    t_end_s: float


W = TypeVar("W", bound=_Window)


@dataclass(frozen=True)
class Thresholds:
    jitter_high: float
    shimmer_high: float
    hnr_low: float
    rate_range: tuple[float, float]
    monotone_st: float
    loudness_flat_std: float


PRESETS: dict[str, Thresholds] = {
    "presentation": Thresholds(
        jitter_high=0.02,
        shimmer_high=0.10,
        hnr_low=10.0,
        # The slow bar matches speech's 110 wpm at about 1.5 syllables a
        # word, so the two pipelines do not disagree on the same talk.
        rate_range=(2.75, 6.0),
        monotone_st=4.0,
        loudness_flat_std=3.0,
    ),
    # Answers are unrehearsed: some nerves, uneven pace and short replies
    # with less melody are expected.
    "qa": Thresholds(
        jitter_high=0.035,
        shimmer_high=0.15,
        hnr_low=8.0,
        rate_range=(2.5, 7.0),
        monotone_st=3.0,
        loudness_flat_std=2.0,
    ),
}


@dataclass(frozen=True)
class VoiceReport:
    mode: str
    pitch: PitchReport
    loudness: LoudnessReport
    nervousness: NervousnessReport
    intonation: IntonationReport
    speaking_rate: SpeakingRateReport
    findings: tuple[Finding, ...]


def thresholds_for(mode: str) -> Thresholds:
    try:
        return PRESETS[mode]
    except KeyError:
        raise ValueError(f"Unknown voice mode {mode!r}. Use one of: {', '.join(PRESETS)}") from None


def _note(start_s: float, end_s: float) -> TimestampedNote:
    return TimestampedNote(int(start_s * 1000), int(end_s * 1000), "")


def _clock(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def _span(start_s: float, end_s: float) -> str:
    return f"{_clock(start_s)}-{_clock(end_s)}"


def stretches(windows: Sequence[W], kind: Callable[[W], str | None]) -> list[tuple[str, list[W]]]:
    """Runs of overlapping or touching windows of the same kind. Windows
    overlap, so one long problem would otherwise give a finding per window."""
    runs: list[tuple[str, list[W]]] = []
    for w in windows:
        k = kind(w)
        if k is None:
            continue
        if runs and runs[-1][0] == k and w.t_start_s <= runs[-1][1][-1].t_end_s:
            runs[-1][1].append(w)
        else:
            runs.append((k, [w]))
    return runs


def _finding(category: str, severity: Severity, summary: str, **kwargs) -> Finding:
    return Finding(
        pipeline=PIPELINE, category=category, severity=severity, summary=summary, **kwargs
    )


def _intonation_findings(intonation: IntonationReport, t: Thresholds) -> list[Finding]:
    narrow = intonation.pitch_range_semitones < t.monotone_st
    flat = intonation.monotone_fraction >= MONOTONE_FRACTION_THRESHOLD
    if not (narrow or flat):
        return []
    return [
        _finding(
            "monotone",
            Severity.MEDIUM,
            f"Pitch moved across only {intonation.pitch_range_semitones:.1f} semitones, and "
            f"{intonation.monotone_fraction:.0%} of the talk had little pitch movement.",
            details={
                "pitch_range_semitones": intonation.pitch_range_semitones,
                "monotone_fraction": intonation.monotone_fraction,
            },
        )
    ]


def _energy_findings(loudness: LoudnessReport, t: Thresholds) -> list[Finding]:
    findings = []
    if loudness.std_db < t.loudness_flat_std:
        findings.append(
            _finding(
                "flat_energy",
                Severity.LOW,
                f"Loudness varied by only {loudness.std_db:.1f} dB, so there was little emphasis.",
                details={"loudness_std_db": loudness.std_db},
            )
        )
    bar = loudness.mean_db - LOUDNESS_DROP_DB
    runs = stretches(loudness.windows, lambda w: "loudness_drop" if w.mean_db < bar else None)
    worst = sorted((min(run, key=lambda w: w.mean_db), run) for _, run in runs)
    for w, run in worst[:MAX_WINDOW_FINDINGS]:
        start, end = run[0].t_start_s, run[-1].t_end_s
        findings.append(
            _finding(
                "loudness_drop",
                Severity.LOW,
                f"Volume dropped at {_span(start, end)} (down to {w.mean_db:.1f} dB against "
                f"your usual {loudness.mean_db:.1f} dB).",
                note=_note(start, end),
                details={
                    "window_mean_db": w.mean_db,
                    "global_mean_db": loudness.mean_db,
                    "windows": len(run),
                },
            )
        )
    return findings


def _nervousness_findings(nervousness: NervousnessReport, t: Thresholds) -> list[Finding]:
    findings = []
    if nervousness.jitter_local > t.jitter_high:
        findings.append(
            _finding(
                "high_jitter",
                Severity.MEDIUM,
                f"Voice jitter was {nervousness.jitter_local:.3f} (above {t.jitter_high}), "
                "which can sound tense.",
                details={"jitter_local": nervousness.jitter_local},
            )
        )
    if nervousness.shimmer_local > t.shimmer_high:
        findings.append(
            _finding(
                "high_shimmer",
                Severity.LOW,
                f"Voice shimmer was {nervousness.shimmer_local:.3f} (above {t.shimmer_high}), "
                "which can sound breathy.",
                details={"shimmer_local": nervousness.shimmer_local},
            )
        )
    if nervousness.hnr_db < t.hnr_low:
        findings.append(
            _finding(
                "low_hnr",
                Severity.MEDIUM,
                f"Harmonics-to-noise ratio was {nervousness.hnr_db:.1f} dB (below "
                f"{t.hnr_low} dB), so the voice sounds breathy or strained.",
                details={"hnr_db": nervousness.hnr_db},
            )
        )

    # A spike is measured against the speaker's own level as well as the
    # fixed bar, so a speaker who is always above the bar is not flagged in
    # every window.
    baseline = nervousness.jitter_local
    spike_at = max(t.jitter_high * 1.5, baseline * JITTER_SPIKE_FACTOR)
    runs = stretches(nervousness.windows, lambda w: "spike" if w.jitter_local > spike_at else None)
    worst = [(max(run, key=lambda w: w.jitter_local), run) for _, run in runs]
    worst.sort(key=lambda pair: -pair[0].jitter_local)
    for w, run in worst[:MAX_WINDOW_FINDINGS]:
        start, end = run[0].t_start_s, run[-1].t_end_s
        findings.append(
            _finding(
                "nervousness_spike",
                Severity.MEDIUM,
                f"Your voice was shaky at {_span(start, end)} (jitter up to "
                f"{w.jitter_local:.3f} against your usual {baseline:.3f}).",
                note=_note(start, end),
                details={
                    "jitter_local": w.jitter_local,
                    "shimmer_local": w.shimmer_local,
                    "hnr_db": w.hnr_db,
                    "windows": len(run),
                },
            )
        )
    return findings


def _pitch_window_findings(pitch: PitchReport) -> list[Finding]:
    high = pitch.mean_hz * PITCH_WINDOW_DEVIATION_FACTOR
    low = pitch.mean_hz / PITCH_WINDOW_DEVIATION_FACTOR

    def kind(w: PitchWindow) -> str | None:
        if w.mean_hz > high:
            return "pitch_too_high"
        if 0 < w.mean_hz < low:
            return "pitch_too_low"
        return None

    off = lambda w: abs(w.mean_hz - pitch.mean_hz)  # noqa: E731
    worst = [(category, max(run, key=off), run) for category, run in stretches(pitch.windows, kind)]
    worst.sort(key=lambda item: -off(item[1]))
    findings = []
    for category, w, run in worst[:MAX_WINDOW_FINDINGS]:
        start, end = run[0].t_start_s, run[-1].t_end_s
        findings.append(
            _finding(
                category,
                Severity.LOW,
                f"Pitch {'rose' if category == 'pitch_too_high' else 'dropped'} at "
                f"{_span(start, end)} ({w.mean_hz:.0f} Hz against your usual "
                f"{pitch.mean_hz:.0f} Hz).",
                note=_note(start, end),
                details={
                    "window_mean_hz": w.mean_hz,
                    "global_mean_hz": pitch.mean_hz,
                    "windows": len(run),
                },
            )
        )
    return findings


def _rate_findings(rate: SpeakingRateReport, t: Thresholds) -> list[Finding]:
    low, high = t.rate_range
    findings = []
    if not low <= rate.global_sps <= high:
        fast = rate.global_sps > high
        findings.append(
            _finding(
                "voice_pace_too_fast" if fast else "voice_pace_too_slow",
                Severity.LOW,
                f"You spoke {rate.global_sps:.1f} syllables a second (comfortable: {low}-{high}).",
                details={"speaking_rate_sps": rate.global_sps},
            )
        )

    def kind(w: RateWindow) -> str | None:
        if w.syllables_per_s > high:
            return "pace_spike"
        if 0 < w.syllables_per_s < low:
            return "pace_drop"
        return None

    middle = (low + high) / 2
    off = lambda w: abs(w.syllables_per_s - middle)  # noqa: E731
    worst = [(category, max(run, key=off), run) for category, run in stretches(rate.windows, kind)]
    worst.sort(key=lambda item: -off(item[1]))
    for category, w, run in worst[:MAX_WINDOW_FINDINGS]:
        start, end = run[0].t_start_s, run[-1].t_end_s
        findings.append(
            _finding(
                category,
                Severity.LOW,
                f"You spoke too {'fast' if category == 'pace_spike' else 'slowly'} at "
                f"{_span(start, end)} ({w.syllables_per_s:.1f} syllables a second, "
                f"comfortable: {low}-{high}).",
                note=_note(start, end),
                details={"window_sps": w.syllables_per_s, "windows": len(run)},
            )
        )
    return findings


def analyze_voice(signal: AudioSignal, mode: AnalysisMode = "presentation") -> VoiceReport:
    t = thresholds_for(mode)
    pitch = analyze_pitch(signal)
    loudness = analyze_loudness(signal)
    nervousness = analyze_nervousness(signal)
    intonation = analyze_intonation(pitch)
    rate = analyze_rate(signal, pitch)

    if signal.duration_s < MIN_DURATION_S or pitch.voiced_fraction == 0:
        findings = [
            _finding(
                "no_voice",
                Severity.INFO,
                "No voice was found in the recording, so the voice was not measured.",
            )
        ]
    else:
        findings = [
            *_intonation_findings(intonation, t),
            *_energy_findings(loudness, t),
            *_nervousness_findings(nervousness, t),
            *_rate_findings(rate, t),
            *_pitch_window_findings(pitch),
        ]
    findings.sort(key=lambda f: (-f.severity.rank, f.note.t_start_ms if f.note else -1))

    return VoiceReport(
        mode=mode,
        pitch=pitch,
        loudness=loudness,
        nervousness=nervousness,
        intonation=intonation,
        speaking_rate=rate,
        findings=tuple(findings),
    )


def score_voice(
    audio: str | Path,
    store: MediaStore | None = None,
    *,
    mode: AnalysisMode = "presentation",
) -> VoiceReport:
    """Analyse a recording given as a local path or a storage key."""
    thresholds_for(mode)  # fail before any download
    with local_media(audio, store) as path:
        signal = load_audio(path)
    return analyze_voice(signal, mode)
