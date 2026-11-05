"""One-paragraph summaries for the debrief, one per voice measure, plus a
combined narrative. Templates only; there is no LLM in the voice pipeline.
"""

from __future__ import annotations

from .loudness import LoudnessReport
from .pitch import PitchReport
from .quality import NervousnessReport
from .rate import SpeakingRateReport
from .report import VoiceReport, thresholds_for

# Pitch range in semitones: below NARROW sounds monotone, above WIDE is
# very expressive.
NARROW_RANGE_ST = 4.0
WIDE_RANGE_ST = 12.0
# Window pitch this far from the mean is worth naming.
PITCH_MENTION_FACTOR = 1.3
# A loudness window this many dB under the mean is worth naming.
LOUDNESS_MENTION_DB = 6.0
# Start and end pace differ by this factor before we call it a trend.
RATE_TREND_FACTOR = 1.25


def _clock(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def _span(start_s: float, end_s: float) -> str:
    return f"{_clock(start_s)}-{_clock(end_s)}"


def summarize_pitch(pitch: PitchReport) -> str:
    if pitch.mean_hz <= 0:
        return "No voiced speech was found to measure pitch."
    if pitch.range_semitones < NARROW_RANGE_ST:
        quality = "narrow, so it can sound monotone"
    elif pitch.range_semitones < WIDE_RANGE_ST:
        quality = "moderate, with fair variety"
    else:
        quality = "wide and expressive"
    text = (
        f"Your pitch averaged {pitch.mean_hz:.0f} Hz over a range of "
        f"{pitch.range_semitones:.1f} semitones, which is {quality}."
    )
    highs = [w for w in pitch.windows if w.mean_hz > pitch.mean_hz * PITCH_MENTION_FACTOR]
    lows = [w for w in pitch.windows if 0 < w.mean_hz < pitch.mean_hz / PITCH_MENTION_FACTOR]
    if highs:
        w = max(highs, key=lambda w: w.mean_hz)
        text += f" It peaked at {_span(w.t_start_s, w.t_end_s)} ({w.mean_hz:.0f} Hz)."
    if lows:
        w = min(lows, key=lambda w: w.mean_hz)
        text += f" It dipped at {_span(w.t_start_s, w.t_end_s)} ({w.mean_hz:.0f} Hz)."
    return text


def summarize_loudness(loudness: LoudnessReport) -> str:
    if loudness.active_fraction == 0:
        return "No sound was loud enough to measure."
    if loudness.std_db < 3.0:
        desc = "very even, with little emphasis"
    elif loudness.std_db < 6.0:
        desc = "steady, with some emphasis"
    else:
        desc = "dynamic, with clear emphasis"
    text = f"Your volume was {desc} (spread {loudness.std_db:.1f} dB)."
    drops = [w for w in loudness.windows if w.mean_db < loudness.mean_db - LOUDNESS_MENTION_DB]
    if drops:
        w = min(drops, key=lambda w: w.mean_db)
        text += (
            f" It fell at {_span(w.t_start_s, w.t_end_s)} "
            f"({w.mean_db:.1f} dB against your usual {loudness.mean_db:.1f} dB)."
        )
    return text


def summarize_nervousness(nervousness: NervousnessReport, mode: str = "presentation") -> str:
    if not nervousness.voiced:
        return "No voiced speech was found to measure voice quality."
    t = thresholds_for(mode)
    if nervousness.jitter_local <= t.jitter_high and nervousness.hnr_db >= t.hnr_low:
        return "Your voice was steady, with no clear sign of nerves."
    text = (
        f"Your voice showed some tension (jitter {nervousness.jitter_local:.3f}, "
        f"HNR {nervousness.hnr_db:.1f} dB)."
    )
    if nervousness.windows:
        w = max(nervousness.windows, key=lambda w: w.jitter_local)
        if w.jitter_local > nervousness.jitter_local * 1.3:
            text += f" It was shakiest at {_span(w.t_start_s, w.t_end_s)}."
    return text


def summarize_speaking_rate(rate: SpeakingRateReport, mode: str = "presentation") -> str:
    low, high = thresholds_for(mode).rate_range
    if rate.global_sps < low:
        desc = "on the slow side"
    elif rate.global_sps > high:
        desc = "fast"
    else:
        desc = "comfortable"
    text = f"You spoke {rate.global_sps:.1f} syllables a second, which is {desc}."

    timed = [w for w in rate.windows if w.syllables_per_s > 0]
    if len(timed) >= 3:
        start = sum(w.syllables_per_s for w in timed[:2]) / 2
        end = sum(w.syllables_per_s for w in timed[-2:]) / 2
        if start > end * RATE_TREND_FACTOR:
            text += f" You started faster ({start:.1f}) and slowed towards the end ({end:.1f})."
        elif end > start * RATE_TREND_FACTOR:
            text += f" You started slower ({start:.1f}) and sped up towards the end ({end:.1f})."
        fastest = max(timed, key=lambda w: w.syllables_per_s)
        slowest = min(timed, key=lambda w: w.syllables_per_s)
        if fastest.syllables_per_s > high:
            text += f" The fastest part was {_span(fastest.t_start_s, fastest.t_end_s)}."
        if slowest.syllables_per_s < low:
            text += f" The slowest part was {_span(slowest.t_start_s, slowest.t_end_s)}."
    return text


def voice_narrative(report: VoiceReport) -> str:
    """All four summaries and an overall line, for one combined write-up."""
    problems = [f for f in report.findings if f.severity.rank > 0]
    if not problems:
        overall = "Overall: no issues found, a strong vocal delivery."
    elif len(problems) <= 3:
        overall = f"Overall: {len(problems)} thing(s) to work on, but a solid delivery."
    else:
        overall = (
            f"Overall: {len(problems)} things to work on. Start with the most severe for the "
            "biggest gain."
        )
    return "\n\n".join(
        [
            summarize_pitch(report.pitch),
            summarize_loudness(report.loudness),
            summarize_speaking_rate(report.speaking_rate, report.mode),
            summarize_nervousness(report.nervousness, report.mode),
            overall,
        ]
    )
