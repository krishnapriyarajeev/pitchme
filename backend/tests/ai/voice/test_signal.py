import shutil

import numpy as np
import pytest

from ai.voice.signal import AudioSignal, load_audio, windows

from .synth import SR, tone, write_wav

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def test_windows_overlap_and_drop_a_tiny_tail():
    assert list(windows(40.5)) == [(0.0, 15.0), (10.0, 25.0), (20.0, 35.0), (30.0, 40.5)]
    assert list(windows(30.5)) == [(0.0, 15.0), (10.0, 25.0), (20.0, 30.5)]
    assert list(windows(25.0)) == [(0.0, 15.0), (10.0, 25.0)]


def test_short_audio_has_one_window_or_none():
    assert list(windows(4.0)) == [(0.0, 4.0)]
    assert list(windows(0.5)) == []


def test_16k_mono_wav_is_read_without_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr("ai.voice.signal.extract_audio", None)  # must not be called
    path = write_wav(tmp_path / "a.wav", tone(1.0, amplitude=0.5))
    signal = load_audio(path)
    assert signal.sample_rate == SR
    assert signal.duration_s == pytest.approx(1.0)
    assert np.abs(signal.samples).max() == pytest.approx(0.5, abs=0.01)


@needs_ffmpeg
def test_other_formats_go_through_ffmpeg(tmp_path):
    samples = tone(44_100 / SR)  # 44 100 samples: 1 s at 44.1 kHz
    path = write_wav(tmp_path / "stereo.wav", samples, rate=44_100, channels=2)
    signal = load_audio(path)
    assert signal.sample_rate == SR
    assert signal.duration_s == pytest.approx(1.0, abs=0.01)
    assert not (tmp_path / "stereo.16k.wav").exists()


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_audio(tmp_path / "nope.wav")


def test_to_sound():
    sound = AudioSignal(tone(0.5), SR).to_sound()
    assert sound.sampling_frequency == SR
    assert sound.get_total_duration() == pytest.approx(0.5)
