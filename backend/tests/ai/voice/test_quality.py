import pytest

from ai.voice.quality import analyze_nervousness

from .synth import cycles, noisy, signal, silence


def test_steady_voice_has_low_jitter_and_shimmer_and_clean_hnr():
    report = analyze_nervousness(signal(cycles(3.0)))
    assert report.voiced
    assert report.jitter_local < 0.005
    assert report.shimmer_local < 0.02
    assert report.hnr_db > 20
    assert len(report.windows) == 1


def test_wobbling_cycle_length_raises_jitter():
    report = analyze_nervousness(signal(cycles(3.0, period_jitter=0.06)))
    # Uniform +-6% per cycle gives about 4% mean change between neighbours.
    assert report.jitter_local == pytest.approx(0.04, abs=0.015)


def test_wobbling_cycle_loudness_raises_shimmer():
    steady = analyze_nervousness(signal(cycles(3.0)))
    shaky = analyze_nervousness(signal(cycles(3.0, amplitude_jitter=0.3)))
    assert shaky.shimmer_local > 0.1
    assert shaky.shimmer_local > 5 * steady.shimmer_local


def test_noise_lowers_hnr():
    clean = analyze_nervousness(signal(cycles(3.0)))
    breathy = analyze_nervousness(signal(noisy(cycles(3.0), noise=0.15)))
    assert breathy.hnr_db < 10
    assert breathy.hnr_db < clean.hnr_db - 10


def test_pauses_do_not_drag_hnr_down():
    with_pauses = analyze_nervousness(signal(cycles(2.0), silence(2.0), cycles(2.0)))
    assert with_pauses.hnr_db > 20


def test_windows_track_a_change_over_the_talk():
    report = analyze_nervousness(signal(cycles(15.0), cycles(15.0, period_jitter=0.08)))
    first, last = report.windows[0], report.windows[-1]
    assert last.jitter_local > 5 * first.jitter_local
    assert (first.t_start_s, last.t_end_s) == (0.0, 30.0)


def test_silence_is_not_voiced():
    report = analyze_nervousness(signal(silence(2.0)))
    assert not report.voiced
    assert report.windows == ()
    assert (report.jitter_local, report.shimmer_local, report.hnr_db) == (0.0, 0.0, 0.0)


def test_silent_window_is_skipped():
    report = analyze_nervousness(signal(cycles(12.0), silence(14.0)))
    assert [(w.t_start_s, w.t_end_s) for w in report.windows] == [(0.0, 15.0), (10.0, 25.0)]
