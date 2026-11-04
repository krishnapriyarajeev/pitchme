from pathlib import Path

import pytest

from ai.core.types import Severity
from ai.voice.report import PRESETS, analyze_voice, score_voice, thresholds_for

from .synth import cycles, glide, noisy, signal, silence, syllables, tone, write_wav


def _categories(report):
    return [f.category for f in report.findings]


def lively(seconds: int):
    """A voice that rises and falls, with syllables at 4.5 a second."""
    rises = [glide(1.0, 110, 190), glide(1.0, 190, 110)] * (seconds // 2)
    shape = syllables(seconds, 4.5)
    voice = signal(*rises).samples
    n = min(voice.size, shape.size)
    envelope = (shape[:n] != 0) * 1.0
    return voice[:n] * (0.3 + 0.7 * envelope)


def test_lively_voice_has_few_findings():
    report = analyze_voice(signal(lively(30)))
    assert report.mode == "presentation"
    assert "monotone" not in _categories(report)
    assert "high_jitter" not in _categories(report)
    assert report.pitch.voiced_fraction > 0.5


def test_flat_tone_is_monotone_and_flat_energy():
    report = analyze_voice(signal(tone(8.0, hz=140)))
    assert {"monotone", "flat_energy"} <= set(_categories(report))
    monotone = next(f for f in report.findings if f.category == "monotone")
    assert monotone.severity is Severity.MEDIUM
    assert monotone.details["monotone_fraction"] == 1.0


def test_shaky_voice_raises_jitter_and_spike():
    report = analyze_voice(signal(cycles(15.0), cycles(15.0, period_jitter=0.1)))
    categories = _categories(report)
    assert "high_jitter" in categories
    spikes = [f for f in report.findings if f.category == "nervousness_spike"]
    assert spikes
    # The steady first window is never a spike.
    assert all(f.note.t_start_ms >= 10_000 for f in spikes)
    assert "0:10-0:25" in spikes[0].summary or "0:20-0:30" in spikes[0].summary


def test_breathy_voice_has_low_hnr_and_high_shimmer():
    report = analyze_voice(signal(noisy(cycles(5.0, amplitude_jitter=0.4), noise=0.2)))
    assert {"low_hnr", "high_shimmer"} <= set(_categories(report))


def test_quiet_stretch_is_a_loudness_drop():
    talk = signal(cycles(20.0, amplitude=0.5), cycles(15.0, amplitude=0.08), cycles(10.0))
    report = analyze_voice(talk)
    drops = [f for f in report.findings if f.category == "loudness_drop"]
    assert 1 <= len(drops) <= 3
    assert drops[0].details["window_mean_db"] < drops[0].details["global_mean_db"] - 8


def test_pitch_jump_is_a_window_finding():
    report = analyze_voice(signal(cycles(30.0, hz=120), cycles(15.0, hz=300)))
    high = [f for f in report.findings if f.category == "pitch_too_high"]
    assert high
    assert high[0].note.t_start_ms >= 20_000


def test_rushed_stretch_is_a_pace_spike_and_slow_talk_is_too_slow():
    rushed = analyze_voice(signal(syllables(15.0, 4.0), syllables(15.0, 7.5)))
    assert "pace_spike" in _categories(rushed)

    slow = analyze_voice(signal(syllables(12.0, 2.0)))
    assert "voice_pace_too_slow" in _categories(slow)
    assert "pace_drop" in _categories(slow)


def test_qa_mode_is_more_lenient_and_its_rate_range_applies_to_windows():
    talk = signal(syllables(30.0, 6.6))
    presentation = analyze_voice(talk, "presentation")
    qa = analyze_voice(talk, "qa")
    assert "pace_spike" in _categories(presentation)
    assert "voice_pace_too_fast" in _categories(presentation)
    assert "pace_spike" not in _categories(qa)
    assert "voice_pace_too_fast" not in _categories(qa)
    assert qa.mode == "qa"


def test_silence_gives_one_info_finding():
    report = analyze_voice(signal(silence(3.0)))
    assert _categories(report) == ["no_voice"]
    assert report.findings[0].severity is Severity.INFO


def test_findings_are_most_severe_first():
    report = analyze_voice(signal(noisy(cycles(20.0, period_jitter=0.08), noise=0.2)))
    ranks = [f.severity.rank for f in report.findings]
    assert ranks == sorted(ranks, reverse=True)
    assert all(f.pipeline == "voice" for f in report.findings)


def test_unknown_mode():
    with pytest.raises(ValueError, match="Unknown voice mode 'debate'"):
        thresholds_for("debate")
    with pytest.raises(ValueError):
        score_voice("never-downloaded.wav", mode="debate")
    assert set(PRESETS) == {"presentation", "qa"}


def test_score_voice_from_a_path_and_from_storage(tmp_path):
    path = write_wav(tmp_path / "talk.wav", tone(3.0))
    assert "monotone" in _categories(score_voice(path))

    class Store:
        def get_file(self, key: str, dest: str | Path) -> Path:
            assert key == "users/1/voice.wav"
            write_wav(Path(dest), tone(3.0))
            return Path(dest)

    report = score_voice("users/1/voice.wav", Store(), mode="qa")
    assert report.mode == "qa"
