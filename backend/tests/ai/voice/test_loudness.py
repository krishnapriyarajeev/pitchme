import numpy as np
import pytest

from ai.voice.loudness import FLOOR_DB, analyze_loudness, rms_db

from .synth import SR, signal, silence, tone


def test_sine_level_matches_theory():
    # RMS of a sine is amplitude / sqrt(2): 0.5 gives -9.03 dBFS.
    report = analyze_loudness(signal(tone(3.0, amplitude=0.5)))
    assert report.mean_db == pytest.approx(-9.0, abs=0.2)
    assert report.std_db < 0.2
    assert report.active_fraction > 0.95


def test_pauses_do_not_count_as_speech():
    talk = signal(tone(2.0), silence(2.0), tone(2.0))
    report = analyze_loudness(talk)
    # Only the frames that straddle a boundary sit between the two levels.
    assert report.std_db < 2
    assert report.min_db > -20
    assert report.active_fraction == pytest.approx(0.67, abs=0.05)


def test_quiet_window_shows_a_drop():
    talk = signal(tone(15.0, amplitude=0.5), tone(15.0, amplitude=0.05))
    report = analyze_loudness(talk)
    assert report.windows[0].mean_db == pytest.approx(-9.0, abs=0.3)
    assert report.windows[-1].mean_db == pytest.approx(-29.0, abs=0.3)
    assert report.std_db > 8


def test_a_window_that_is_mostly_pause_is_skipped():
    talk = signal(tone(15.0), silence(14.0), tone(1.0))
    report = analyze_loudness(talk)
    assert [(w.t_start_s, w.t_end_s) for w in report.windows] == [(0.0, 15.0), (10.0, 25.0)]


def test_silence():
    report = analyze_loudness(signal(silence(2.0)))
    assert report.mean_db == FLOOR_DB
    assert report.active_fraction == 0.0
    assert report.windows == ()


def test_rms_frames_and_short_input():
    times, db = rms_db(np.zeros(100, dtype=np.float32), SR)
    assert len(times) == len(db) == 1
    assert db[0] == FLOOR_DB
    times, _ = rms_db(tone(1.0), SR)
    assert np.all(np.diff(times) > 0)
