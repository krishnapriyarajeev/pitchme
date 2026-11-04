import pytest

from ai.providers.groq.whisper import GroqWhisperClient, parse_verbose_json
from ai.transcribe import TranscribeError

from .fakes import FakeTranscriptions

# Shape of a real verbose_json reply, trimmed.
REPLY = {
    "text": " Thanks for the time. Our ARR is four crore.",
    "language": "English",
    "segments": [
        {"start": 0.0, "end": 1.4, "text": " Thanks for the time.", "avg_logprob": -0.21},
        {"start": 2.0, "end": 4.1, "text": " Our ARR is four crore.", "avg_logprob": -0.35},
    ],
    "words": [
        {"word": "Thanks", "start": 0.0, "end": 0.4},
        {"word": "for", "start": 0.4, "end": 0.6},
        {"word": "the", "start": 0.6, "end": 0.7},
        {"word": "time.", "start": 0.7, "end": 1.4},
        # Starts in the pause before segment 2: stays with segment 1.
        {"word": "Our", "start": 1.8, "end": 2.2},
        {"word": "ARR", "start": 2.2, "end": 2.7},
        {"word": "is", "start": 2.7, "end": 2.9},
        {"word": "four", "start": 2.9, "end": 3.3},
        {"word": "crore.", "start": 3.3, "end": 4.1},
    ],
}


def test_parse_groups_words_by_time():
    transcript = parse_verbose_json(REPLY)
    first, second = transcript.segments
    assert first.text == "Thanks for the time."
    assert [w.text for w in first.words] == ["Thanks", "for", "the", "time.", "Our"]
    assert [w.text for w in second.words] == ["ARR", "is", "four", "crore."]
    assert second.start_ms == 2000
    assert second.end_ms == 4100
    assert transcript.language == "English"


def test_parse_keeps_confidence_per_segment_only():
    transcript = parse_verbose_json(REPLY)
    assert transcript.segments[0].confidence == -0.21
    assert all(word.logprob is None for word in transcript.words)


def test_word_before_first_segment_is_kept():
    data = {
        "text": "hello",
        "segments": [{"start": 0.5, "end": 1.0, "text": "hello"}],
        "words": [{"word": "hello", "start": 0.4, "end": 1.0}],
    }
    assert [w.text for w in parse_verbose_json(data).words] == ["hello"]


@pytest.mark.parametrize("data", [{}, {"text": "  ", "segments": []}, {"text": "x"}])
def test_no_speech_gives_empty_transcript(data):
    assert parse_verbose_json(data).is_empty


def test_transcribe_sends_file_and_options(tmp_path):
    audio = tmp_path / "call.wav"
    audio.write_bytes(b"RIFF fake")
    fake = FakeTranscriptions(REPLY)

    transcript = GroqWhisperClient(client=fake, model="w").transcribe(audio)

    assert transcript.text.startswith("Thanks")
    call = fake.calls[0]
    assert call["model"] == "w"
    assert call["file"] == ("call.wav", b"RIFF fake")
    assert call["response_format"] == "verbose_json"
    assert call["timestamp_granularities"] == ["word", "segment"]


def test_missing_file(tmp_path):
    with pytest.raises(TranscribeError, match="not found"):
        GroqWhisperClient(client=FakeTranscriptions()).transcribe(tmp_path / "nope.wav")


def test_wraps_sdk_errors(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    fake = FakeTranscriptions(error=RuntimeError("413 file too large"))
    with pytest.raises(TranscribeError, match=r"a\.wav: 413"):
        GroqWhisperClient(client=fake).transcribe(audio)


def test_missing_key():
    with pytest.raises(TranscribeError, match="GROQ_API_KEY"):
        GroqWhisperClient(api_key="")
