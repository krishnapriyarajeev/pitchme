import math
import sys
from types import SimpleNamespace as NS

import pytest

from ai.providers.local.whisper import LocalWhisperClient, probability_to_logprob
from ai.transcribe import TranscribeError


def _segment(text, start, end, words, avg_logprob=-0.3):
    return NS(text=text, start=start, end=end, words=words, avg_logprob=avg_logprob)


class FakeModel:
    def __init__(self, segments, error=None):
        self.segments = segments
        self.error = error
        self.calls = []

    def transcribe(self, path, **kwargs):
        self.calls.append((path, kwargs))

        def generate():
            if self.error:
                raise self.error
            yield from self.segments

        return generate(), NS(language="en")


def test_probability_becomes_natural_log():
    assert probability_to_logprob(1.0) == 0.0
    assert probability_to_logprob(0.5) == pytest.approx(math.log(0.5))
    assert math.isfinite(probability_to_logprob(0.0))


def test_transcribe_keeps_per_word_confidence(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    model = FakeModel(
        [
            _segment(
                " Hi there.",
                0.0,
                0.9,
                [
                    NS(word=" Hi", start=0.0, end=0.3, probability=0.9),
                    NS(word=" there.", start=0.3, end=0.9, probability=0.4),
                ],
            ),
            _segment(" Okay.", 1.2, 1.5, None),
        ]
    )

    transcript = LocalWhisperClient(model=model).transcribe(audio)

    assert model.calls[0] == (str(audio), {"word_timestamps": True})
    assert transcript.text == "Hi there. Okay."
    assert [w.text for w in transcript.words] == ["Hi", "there."]
    assert transcript.words[1].logprob == pytest.approx(math.log(0.4))
    assert transcript.segments[0].confidence == -0.3
    assert transcript.segments[1].words == ()


def test_no_speech_gives_empty_transcript(tmp_path):
    audio = tmp_path / "silence.wav"
    audio.write_bytes(b"x")
    assert LocalWhisperClient(model=FakeModel([])).transcribe(audio).is_empty


def test_errors_while_decoding_are_wrapped(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    model = FakeModel([], error=RuntimeError("bad codec"))
    with pytest.raises(TranscribeError, match="bad codec"):
        LocalWhisperClient(model=model).transcribe(audio)


def test_missing_package_is_explained(monkeypatch):
    # None in sys.modules makes the import fail, installed or not.
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(TranscribeError, match="whisper-local"):
        LocalWhisperClient()
