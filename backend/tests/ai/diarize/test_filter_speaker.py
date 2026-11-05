from dataclasses import dataclass

import numpy as np
import pytest

from ai.core.transcript import Segment, Transcript, Word
from ai.diarize.align import tag_speakers
from ai.diarize.base import DiarizedSegment as D
from ai.diarize.filter_speaker import filter_audio, filter_transcript, kept_ranges


def test_other_speakers_turns_are_cut_out():
    segments = (D("A", 0, 2000), D("B", 2000, 5000), D("A", 5000, 6000))
    assert kept_ranges(segments, "A", 6000) == [(0, 2000), (5000, 6000)]
    assert kept_ranges(segments, "B", 6000) == [(2000, 5000)]


def test_overlap_and_uncovered_silence_are_kept():
    segments = (D("A", 0, 3000), D("B", 2500, 5000), D("A", 7000, 8000))
    # 2500-3000 both talk: kept. 5000-7000 nobody: kept. Only 3000-5000 goes.
    assert kept_ranges(segments, "A", 9000) == [(0, 3000), (5000, 9000)]


def test_one_speaker_keeps_everything():
    assert kept_ranges((D("A", 0, 3000),), "A", 4000) == [(0, 4000)]


def _call() -> tuple[Transcript, tuple[D, ...]]:
    """User (A) asks, buyer (B) answers for 3 s, user goes on."""
    words = (
        Word("our", 0, 300, -0.1),
        Word("price", 400, 900, -0.2),
        Word("too", 2100, 2400),
        Word("high", 2500, 4800),
        Word("fair", 5100, 5500, -0.3),
        Word("point", 5600, 6000, -0.4),
    )
    transcript = Transcript(
        segments=(
            Segment("our price", 0, 900, words[:2], confidence=-0.2),
            Segment("too high", 2100, 4800, words[2:4]),
            Segment("fair point", 5100, 6000, words[4:], confidence=-0.3),
        )
    )
    return transcript, (D("A", 0, 2000), D("B", 2000, 5000), D("A", 5000, 6000))


def test_transcript_keeps_one_speaker_with_the_gap_closed():
    transcript, segments = _call()
    user = filter_transcript(tag_speakers(transcript, segments), "A", segments)
    assert [(w.text, w.start_ms, w.end_ms, w.logprob) for w in user.words] == [
        ("our", 0, 300, -0.1),
        ("price", 400, 900, -0.2),
        ("fair", 2100, 2500, -0.3),
        ("point", 2600, 3000, -0.4),
    ]
    assert [s.text for s in user.segments] == ["our price", "fair point"]
    assert user.segments[1].confidence == -0.3
    assert user.duration_ms == 3000


def test_buyer_only_transcript():
    transcript, segments = _call()
    buyer = filter_transcript(tag_speakers(transcript, segments), "B", segments)
    assert [(w.text, w.start_ms) for w in buyer.words] == [("too", 100), ("high", 500)]


def test_closed_gap_is_not_a_pause_any_more():
    from ai.speech.fluency import find_pauses

    transcript, segments = _call()
    user = filter_transcript(tag_speakers(transcript, segments), "A", segments)
    # Before filtering, "price" to "fair" was a 4.2 s gap; now it is 1.2 s.
    assert [p.duration_ms for p in find_pauses(user.words)] == [1200]


@dataclass(frozen=True, eq=False)
class Signal:
    samples: np.ndarray
    sample_rate: int


def test_audio_keeps_one_speakers_samples_end_to_end():
    rate = 1000  # one sample per ms keeps the arithmetic readable
    samples = np.concatenate([np.full(2000, 1.0), np.full(3000, 2.0), np.full(1000, 3.0)])
    segments = (D("A", 0, 2000), D("B", 2000, 5000), D("A", 5000, 6000))
    user = filter_audio(Signal(samples, rate), segments, "A")
    assert isinstance(user, Signal)
    assert user.sample_rate == rate
    assert len(user.samples) == 3000
    assert set(np.unique(user.samples)) == {1.0, 3.0}


def test_audio_with_only_the_other_speaker_is_empty():
    signal = Signal(np.ones(1000, dtype=np.float32), 1000)
    out = filter_audio(signal, (D("B", 0, 1000),), "A")
    assert out.samples.size == 0
    assert out.samples.dtype == np.float32


def test_works_with_the_voice_pipelines_signal():
    voice = pytest.importorskip("ai.voice")
    signal = voice.AudioSignal(np.ones(16_000, dtype=np.float32), 16_000)
    out = filter_audio(signal, (D("A", 0, 500), D("B", 500, 1000)), "A")
    assert isinstance(out, voice.AudioSignal)
    assert out.duration_s == pytest.approx(0.5)
