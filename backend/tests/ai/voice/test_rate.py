import numpy as np
import pytest

from ai.voice.rate import analyze_rate, syllable_times

from .synth import SR, noisy, signal, silence, syllables


@pytest.mark.parametrize("per_second", [3.0, 4.5, 6.0])
def test_counts_syllables_at_a_known_rate(per_second):
    report = analyze_rate(signal(syllables(8.0, per_second)))
    assert report.global_sps == pytest.approx(per_second, abs=0.3)
    assert report.syllable_count == pytest.approx(8 * per_second, abs=2)


def test_pauses_lower_the_rate():
    report = analyze_rate(signal(syllables(4.0, 5.0), silence(4.0)))
    assert report.global_sps == pytest.approx(2.5, abs=0.3)


def test_windows_track_a_speed_up():
    report = analyze_rate(signal(syllables(15.0, 3.0), syllables(15.0, 6.0)))
    first, last = report.windows[0], report.windows[-1]
    assert first.syllables_per_s == pytest.approx(3.0, abs=0.3)
    assert last.syllables_per_s == pytest.approx(6.0, abs=0.4)


def test_unvoiced_noise_bursts_are_not_syllables():
    rng = np.random.default_rng(1)
    envelope = np.tile(np.r_[np.hanning(2_400), np.zeros(1_600)], 16)
    bursts = (envelope * rng.normal(0, 0.3, envelope.size)).astype(np.float32)
    assert analyze_rate(signal(bursts)).syllable_count <= 2


def test_light_background_noise_is_ignored():
    report = analyze_rate(signal(noisy(syllables(6.0, 4.0), noise=0.005)))
    assert report.global_sps == pytest.approx(4.0, abs=0.4)


def test_silence_and_empty_audio():
    assert analyze_rate(signal(silence(2.0))).global_sps == 0.0
    empty = signal(np.zeros(0, dtype=np.float32))
    assert analyze_rate(empty).global_sps == 0.0
    assert syllable_times(signal(np.zeros(SR // 50, dtype=np.float32))).size == 0
