import pytest

from ai.diarize.base import DiarizedSegment, DiarizeError, speaking_time
from ai.providers.pyannote.diarizer import PyannoteDiarizer, load_pretrained

from .fakes import FakePipeline


@pytest.fixture
def audio(tmp_path):
    path = tmp_path / "call.wav"
    path.write_bytes(b"RIFF")
    return path


@pytest.mark.parametrize("wrapped", [False, True])
def test_turns_become_sorted_segments_in_ms(audio, wrapped):
    pipeline = FakePipeline(
        [(2.5, 4.0, "SPEAKER_01"), (0.0, 2.4, "SPEAKER_00"), (3.0, 3.0, "SPEAKER_00")],
        wrapped=wrapped,
    )
    segments = PyannoteDiarizer(pipeline=pipeline).diarize(audio, max_speakers=3)
    assert segments == (
        DiarizedSegment("SPEAKER_00", 0, 2400),
        DiarizedSegment("SPEAKER_01", 2500, 4000),
    )
    assert pipeline.calls == [(str(audio), {"min_speakers": 1, "max_speakers": 3})]


def test_silence_gives_no_segments(audio):
    assert PyannoteDiarizer(pipeline=FakePipeline([])).diarize(audio) == ()


def test_missing_audio(tmp_path):
    with pytest.raises(DiarizeError, match="Audio file not found"):
        PyannoteDiarizer(pipeline=FakePipeline([])).diarize(tmp_path / "gone.wav")


def test_pipeline_errors_are_wrapped(audio):
    diarizer = PyannoteDiarizer(pipeline=FakePipeline([], error=RuntimeError("out of memory")))
    with pytest.raises(DiarizeError, match=r"Diarization failed for call\.wav: out of memory"):
        diarizer.diarize(audio)


def test_load_pretrained_supports_both_token_arguments():
    class Four:
        @staticmethod
        def from_pretrained(name, token):
            return ("4", name, token)

    class Three:
        @staticmethod
        def from_pretrained(name, use_auth_token):
            return ("3", name, use_auth_token)

    assert load_pretrained(Four, "m", "t") == ("4", "m", "t")
    assert load_pretrained(Three, "m", "t") == ("3", "m", "t")


def test_speaking_time():
    segments = (
        DiarizedSegment("A", 0, 1000),
        DiarizedSegment("B", 1000, 4000),
        DiarizedSegment("A", 4000, 4500),
    )
    assert speaking_time(segments) == {"B": 3000, "A": 1500}
    assert DiarizedSegment("A", 10, 30).duration_ms == 20
