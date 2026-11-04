import shutil
import subprocess
import wave

import pytest

from ai.utils import audio
from ai.utils.audio import AudioExtractionError, extract_audio

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _make(path, *args):
    """A 1 second test file made by ffmpeg itself."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *args, str(path)], check=True, capture_output=True
    )
    return path


def _tone(path, rate=44_100, channels=2):
    return _make(
        path,
        "-f", "lavfi", "-i", f"sine=frequency=440:duration=1:sample_rate={rate}",
        "-ac", str(channels),
    )  # fmt: skip


def _wav_format(path):
    with wave.open(str(path)) as wav:
        return wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()


@needs_ffmpeg
def test_video_to_16k_mono_wav(tmp_path):
    video = _make(
        tmp_path / "call.mp4",
        "-f", "lavfi", "-i", "color=black:size=64x64:duration=1",
        "-f", "lavfi", "-i", "sine=frequency=300:duration=1",
        "-shortest", "-c:v", "libx264", "-c:a", "aac",
    )  # fmt: skip

    out = extract_audio(video)

    assert out == tmp_path / "call.wav"
    rate, channels, width, frames = _wav_format(out)
    assert (rate, channels, width) == (16_000, 1, 2)
    assert 15_000 < frames <= 17_000


@needs_ffmpeg
def test_m4a_voice_sample(tmp_path):
    sample = _make(
        tmp_path / "voice.m4a",
        "-f", "lavfi", "-i", "sine=frequency=200:duration=1", "-c:a", "aac",
    )  # fmt: skip
    out = extract_audio(sample, tmp_path / "out" / "voice.wav", sample_rate=22_050)
    assert out.parent.name == "out"
    assert _wav_format(out)[:2] == (22_050, 1)


@needs_ffmpeg
def test_wav_input_is_not_overwritten(tmp_path):
    source = _tone(tmp_path / "sample.wav")
    out = extract_audio(source)
    assert out == tmp_path / "sample.16k.wav"
    assert _wav_format(source)[0] == 44_100
    assert _wav_format(out)[0] == 16_000


@needs_ffmpeg
def test_video_without_sound(tmp_path):
    silent = _make(
        tmp_path / "silent.mp4",
        "-f", "lavfi", "-i", "color=black:size=64x64:duration=1", "-c:v", "libx264",
    )  # fmt: skip
    with pytest.raises(AudioExtractionError, match=r"silent\.mp4"):
        extract_audio(silent)


@needs_ffmpeg
def test_not_media(tmp_path):
    junk = tmp_path / "notes.mp4"
    junk.write_text("not a video")
    with pytest.raises(AudioExtractionError, match=r"ffmpeg failed on notes\.mp4"):
        extract_audio(junk)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_audio(tmp_path / "nope.mp4")


def test_missing_ffmpeg(tmp_path, monkeypatch):
    source = tmp_path / "a.mp4"
    source.write_bytes(b"x")
    monkeypatch.setattr(audio.shutil, "which", lambda _: None)
    with pytest.raises(AudioExtractionError, match="not installed"):
        extract_audio(source)
