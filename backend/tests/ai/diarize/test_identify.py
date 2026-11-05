import numpy as np
import pytest

from ai.diarize.base import DiarizedSegment as D
from ai.diarize.base import DiarizeError
from ai.diarize.identify import Identification, cosine, identify_speaker
from ai.providers.pyannote.embedding import PyannoteEmbedder

USER = np.array([1.0, 0.0, 0.0])
BUYER = np.array([0.0, 1.0, 0.0])


class FakeEmbedder:
    """Voices by time: the user before 5 s, the buyer after."""

    def __init__(self, reference=USER):
        self.reference = reference
        self.spans: list[tuple[int, int]] = []

    def embed_file(self, path):
        return self.reference

    def embed_span(self, path, start_ms, end_ms):
        self.spans.append((start_ms, end_ms))
        return USER + 0.1 * BUYER if start_ms < 5000 else BUYER


SEGMENTS = (D("SPEAKER_00", 5000, 9000), D("SPEAKER_01", 0, 4000), D("SPEAKER_01", 9000, 9200))


def test_picks_the_speaker_closest_to_the_voice_sample():
    embedder = FakeEmbedder()
    result = identify_speaker(embedder, "call.wav", SEGMENTS, "sample.wav")
    assert result.speaker == "SPEAKER_01"
    assert result.confident
    assert result.scores["SPEAKER_00"] == 0.0
    assert result.margin == pytest.approx(0.995, abs=0.001)
    # The 200 ms clip is too short to embed.
    assert (9000, 9200) not in embedder.spans


def test_weak_match_is_not_confident():
    reference = np.array([0.1, 0.1, 1.0])
    result = identify_speaker(FakeEmbedder(reference), "call.wav", SEGMENTS, "sample.wav")
    assert not result.confident


def test_no_segments_or_only_short_ones():
    with pytest.raises(DiarizeError, match="No speaker segments"):
        identify_speaker(FakeEmbedder(), "call.wav", (), "sample.wav")
    with pytest.raises(DiarizeError, match="too short to compare"):
        identify_speaker(FakeEmbedder(), "call.wav", (D("A", 0, 100),), "sample.wav")


def test_single_speaker_margin_is_its_score():
    assert Identification("A", {"A": 0.8}).margin == 0.8


def test_cosine():
    assert cosine(USER, USER) == pytest.approx(1.0)
    assert cosine(USER, BUYER) == 0.0
    assert cosine(USER, np.zeros(3)) == 0.0
    assert cosine(np.array([[1.0, 1.0]]), np.array([2.0, 2.0])) == pytest.approx(1.0)


def test_pyannote_embedder_uses_the_whole_window_inference():
    calls = []

    def inference(path):
        calls.append(("file", path))
        return [1.0, 2.0]

    inference.crop = lambda path, span: calls.append(("crop", path, span.start, span.end)) or [3.0]
    pytest.importorskip("pyannote.core", reason="needs the diarize extra")

    class Audio:
        def get_duration(self, path):
            calls.append(("duration", path))
            return 35.012

    embedder = PyannoteEmbedder(inference=inference, audio=Audio())
    assert embedder.embed_file("a.wav").tolist() == [1.0, 2.0]
    assert embedder.embed_span("a.wav", 1500, 3000).tolist() == [3.0]
    # A segment rounded past the end of the file is clamped to it.
    embedder.embed_span("a.wav", 30000, 35063)
    assert calls == [
        ("file", "a.wav"),
        ("duration", "a.wav"),  # read once, then cached
        ("crop", "a.wav", 1.5, 3.0),
        ("crop", "a.wav", 30.0, 35.012),
    ]


def test_pyannote_embedder_needs_a_token():
    with pytest.raises(DiarizeError, match="HF_TOKEN is not set"):
        PyannoteEmbedder("")


def test_pyannote_embedder_without_package(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "pyannote.audio", None)
    with pytest.raises(DiarizeError, match="uv sync --extra diarize"):
        PyannoteEmbedder("test-token-not-used")


def test_embed_file_wraps_the_result():
    embedder = PyannoteEmbedder(inference=lambda path: [0.5])
    assert isinstance(embedder.embed_file("x.wav"), np.ndarray)
