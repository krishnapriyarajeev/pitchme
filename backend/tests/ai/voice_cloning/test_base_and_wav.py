import pytest

from ai.voice_cloning.base import MAX_SPEED, MIN_SPEED, ProsodyParams, VoiceCloneError
from ai.voice_cloning.wav import join_wav, read_wav

from .fakes import RATE, tone_wav


def test_prosody_is_kept_in_range():
    assert ProsodyParams("confident", 1.1, 300) == ProsodyParams("confident", 1.1, 300)
    wild = ProsodyParams("ecstatic", 9.0, -50)
    assert (wild.emotion, wild.speed, wild.pause_after_ms) == ("neutral", MAX_SPEED, 0)
    assert ProsodyParams(speed=0.1).speed == MIN_SPEED


def test_join_makes_one_valid_wav_with_pauses():
    joined = join_wav([tone_wav(500), tone_wav(250)], pauses_ms=[400])
    pcm = read_wav(joined)
    assert (pcm.rate, pcm.channels, pcm.width) == (RATE, 1, 2)
    assert pcm.duration_ms == 1150
    # The pause is real silence.
    start = RATE * 500 // 1000 * 2
    assert set(pcm.frames[start : start + RATE * 400 // 1000 * 2]) == {0}
    # Exactly one header: a naive b"".join would keep both.
    assert joined.count(b"RIFF") == 1


def test_trailing_pause_is_kept():
    assert read_wav(join_wav([tone_wav(100)], [200])).duration_ms == 300


def test_clips_must_share_a_format():
    with pytest.raises(VoiceCloneError, match="Clips differ in format"):
        join_wav([tone_wav(100), tone_wav(100, rate=22_050)])


def test_bad_inputs():
    with pytest.raises(VoiceCloneError, match="No audio clips"):
        join_wav([])
    with pytest.raises(VoiceCloneError, match="not a WAV file"):
        read_wav(b"ID3 mp3 bytes")
