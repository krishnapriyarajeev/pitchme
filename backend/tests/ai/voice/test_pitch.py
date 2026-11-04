import numpy as np
import pytest

from ai.voice.pitch import analyze_intonation, analyze_pitch, semitones

from .synth import glide, signal, silence, tone


def test_steady_tone():
    report = analyze_pitch(signal(tone(3.0, hz=150)))
    assert report.mean_hz == pytest.approx(150, abs=1)
    assert report.range_semitones < 0.2
    assert report.voiced_fraction > 0.9
    assert len(report.hz) == len(report.times_s)
    assert len(report.windows) == 1


def test_octave_glide_spans_about_twelve_semitones():
    report = analyze_pitch(signal(glide(4.0, 110, 220)))
    # The 5th to 95th percentile of an even glide covers 90% of the octave.
    assert report.range_semitones == pytest.approx(10.8, abs=0.6)
    assert report.min_hz == pytest.approx(110, abs=5)
    assert report.max_hz == pytest.approx(220, abs=5)


def test_windows_follow_pitch_over_time():
    report = analyze_pitch(signal(tone(15.0, hz=120), tone(15.0, hz=240)))
    assert [(w.t_start_s, w.t_end_s) for w in report.windows] == [
        (0.0, 15.0),
        (10.0, 25.0),
        (20.0, 30.0),
    ]
    assert report.windows[0].mean_hz == pytest.approx(120, abs=1)
    assert report.windows[-1].mean_hz == pytest.approx(240, abs=1)
    assert report.windows[1].range_semitones > 10


def test_silence_has_no_pitch():
    report = analyze_pitch(signal(silence(2.0)))
    assert report.mean_hz == 0.0
    assert report.voiced_fraction == 0.0
    assert report.windows == ()
    intonation = analyze_intonation(report)
    assert intonation.monotone_fraction == 1.0
    assert intonation.pitch_slope_mean == 0.0


def test_flat_voice_is_monotone():
    intonation = analyze_intonation(analyze_pitch(signal(tone(6.0, hz=140))))
    assert intonation.monotone_fraction == 1.0
    assert intonation.pitch_slope_mean < 1.0


def test_moving_voice_is_not_monotone():
    rises = [glide(1.0, 110, 200), glide(1.0, 200, 110)] * 3
    intonation = analyze_intonation(analyze_pitch(signal(*rises)))
    assert intonation.monotone_fraction == 0.0
    assert intonation.pitch_slope_mean > 5
    assert intonation.pitch_range_semitones > 8


def test_jump_across_a_pause_is_not_a_slide():
    report = analyze_pitch(signal(tone(2.0, 110), silence(0.5), tone(2.0, 220)))
    assert analyze_intonation(report).pitch_slope_mean < 1.0


def test_semitones():
    assert semitones(220, 110) == pytest.approx(12)
    assert semitones(0, 110) == 0.0
    assert np.isclose(semitones(110, 110), 0)
