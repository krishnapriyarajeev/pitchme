from dataclasses import replace

from ai.core.types import Finding, Severity
from ai.voice.loudness import LoudnessReport, LoudnessWindow
from ai.voice.pitch import PitchReport, PitchWindow
from ai.voice.quality import NervousnessReport, NervousnessWindow
from ai.voice.rate import RateWindow, SpeakingRateReport
from ai.voice.report import analyze_voice
from ai.voice.summary import (
    summarize_loudness,
    summarize_nervousness,
    summarize_pitch,
    summarize_speaking_rate,
    voice_narrative,
)

from .synth import signal, tone


def _pitch(range_st, windows=()):
    return PitchReport(150, 20, 100, 250, range_st, 0.8, (), (), tuple(windows))


def test_pitch_summary():
    assert "monotone" in summarize_pitch(_pitch(2.0))
    assert "fair variety" in summarize_pitch(_pitch(8.0))
    windows = [PitchWindow(0, 15, 220, 10, 3), PitchWindow(10, 25, 100, 10, 3)]
    text = summarize_pitch(_pitch(14.0, windows))
    assert "wide and expressive" in text
    assert "peaked at 0:00-0:15 (220 Hz)" in text
    assert "dipped at 0:10-0:25 (100 Hz)" in text
    assert summarize_pitch(replace(_pitch(0), mean_hz=0)).startswith("No voiced")


def _loudness(std, windows=(), active=0.9):
    return LoudnessReport(-20, std, -40, -5, active, (), (), tuple(windows))


def test_loudness_summary():
    assert "little emphasis" in summarize_loudness(_loudness(1.0))
    assert "some emphasis" in summarize_loudness(_loudness(4.0))
    text = summarize_loudness(_loudness(7.0, [LoudnessWindow(60, 75, -30, 2)]))
    assert "clear emphasis" in text
    assert "fell at 1:00-1:15 (-30.0 dB" in text
    assert summarize_loudness(_loudness(0, active=0)).startswith("No sound")


def test_nervousness_summary_depends_on_mode():
    steady = NervousnessReport(0.01, 0.05, 15, ())
    assert "steady" in summarize_nervousness(steady)
    tense = NervousnessReport(0.03, 0.05, 15, (NervousnessWindow(30, 45, 0.06, 0.1, 12),))
    assert "shakiest at 0:30-0:45" in summarize_nervousness(tense)
    assert "steady" in summarize_nervousness(tense, "qa")
    silent = NervousnessReport(0, 0, 0, (), voiced=False)
    assert summarize_nervousness(silent).startswith("No voiced")


def _rate(sps, rates=()):
    windows = tuple(RateWindow(i * 10, i * 10 + 15, r) for i, r in enumerate(rates))
    return SpeakingRateReport(sps, 0, windows)


def test_rate_summary():
    assert "comfortable" in summarize_speaking_rate(_rate(4.5))
    assert "slow side" in summarize_speaking_rate(_rate(2.0))
    assert "comfortable" in summarize_speaking_rate(_rate(2.7), "qa")
    slowing = summarize_speaking_rate(_rate(6.5, [7.0, 6.5, 4.0, 2.5]))
    assert "fast" in slowing
    assert "slowed towards the end" in slowing
    assert "fastest part was 0:00-0:15" in slowing
    assert "slowest part was 0:30-0:45" in slowing
    speeding = summarize_speaking_rate(_rate(4.5, [3.0, 3.2, 4.5, 5.0]))
    assert "sped up towards the end" in speeding


def test_narrative_joins_every_part():
    report = analyze_voice(signal(tone(4.0)))
    text = voice_narrative(report)
    assert text.count("\n\n") == 4
    assert "Overall:" in text


def test_narrative_overall_line_counts_problems():
    report = analyze_voice(signal(tone(4.0)))
    low = Finding("voice", "x", Severity.LOW, "s")
    info = Finding("voice", "y", Severity.INFO, "s")
    assert "no issues" in voice_narrative(replace(report, findings=(info,)))
    assert "1 thing(s)" in voice_narrative(replace(report, findings=(low,)))
    assert "Start with the most severe" in voice_narrative(replace(report, findings=(low,) * 4))
