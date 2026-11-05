"""Articulation from the words side: did the right word land clearly?

The signal is the transcriber's own confidence. Local faster-whisper gives a
log probability per word, so single unclear words are flagged. Groq gives
one value per segment only, so with Groq a whole segment is flagged when
the model was unsure of it. A talk is never judged on a missing value:
words with neither signal are skipped, not counted as clear.

The acoustic side of articulation lives in ai.voice.

A flag also records whether the speaker was rushing at that moment. People
slur when they rush, and the fix for that is pace, not diction.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass

from ai.core.transcript import Segment, Transcript, Word

# Below this per-word log probability Whisper was unsure of the word.
WORD_LOGPROB_THRESHOLD = -0.5

# Below this average log probability Whisper was unsure of the segment.
# Clear speech usually scores between -0.1 and -0.4.
SEGMENT_CONFIDENCE_THRESHOLD = -0.6

# Above this local rate the speaker was rushing.
RATE_SPIKE_WPM = 200
LOCAL_RATE_WINDOW_MS = 5_000


@dataclass(frozen=True)
class ArticulationFlag:
    text: str
    t_start_ms: int
    t_end_ms: int
    logprob: float
    # "word" for a single word, "segment" for a whole low-confidence segment.
    source: str
    word_count: int
    co_occurring_rate_spike: bool


@dataclass(frozen=True)
class ArticulationReport:
    flags: tuple[ArticulationFlag, ...]
    words_checked: int

    @property
    def unclear_words(self) -> int:
        return sum(flag.word_count for flag in self.flags)

    @property
    def clarity_score(self) -> float:
        """Share of checked words that were clear, from 0 to 1."""
        if self.words_checked == 0:
            return 1.0
        return round(1 - self.unclear_words / self.words_checked, 3)


def _local_wpm(starts: list[int], t_start_ms: int, t_end_ms: int) -> float:
    """Rate in a window centred on the given span."""
    centre = (t_start_ms + t_end_ms) // 2
    lo = centre - LOCAL_RATE_WINDOW_MS // 2
    hi = centre + LOCAL_RATE_WINDOW_MS // 2
    count = bisect_right(starts, hi) - bisect_left(starts, lo)
    return count / (LOCAL_RATE_WINDOW_MS / 60_000)


def _segment_flag(segment: Segment, starts: list[int]) -> ArticulationFlag | None:
    if segment.confidence is None or segment.confidence >= SEGMENT_CONFIDENCE_THRESHOLD:
        return None
    return ArticulationFlag(
        text=segment.text,
        t_start_ms=segment.start_ms,
        t_end_ms=segment.end_ms,
        logprob=segment.confidence,
        source="segment",
        word_count=len(segment.words),
        co_occurring_rate_spike=_local_wpm(starts, segment.start_ms, segment.end_ms)
        >= RATE_SPIKE_WPM,
    )


def _word_flag(word: Word, starts: list[int]) -> ArticulationFlag | None:
    if word.logprob is None or word.logprob >= WORD_LOGPROB_THRESHOLD:
        return None
    return ArticulationFlag(
        text=word.text,
        t_start_ms=word.start_ms,
        t_end_ms=word.end_ms,
        logprob=word.logprob,
        source="word",
        word_count=1,
        co_occurring_rate_spike=_local_wpm(starts, word.start_ms, word.end_ms) >= RATE_SPIKE_WPM,
    )


def score_articulation(transcript: Transcript) -> ArticulationReport:
    starts = [w.start_ms for w in transcript.words]
    flags: list[ArticulationFlag] = []
    checked = 0
    for segment in transcript.segments:
        scored = [w for w in segment.words if w.logprob is not None]
        if scored:
            checked += len(scored)
            flags.extend(f for w in scored if (f := _word_flag(w, starts)))
        elif segment.confidence is not None and segment.words:
            checked += len(segment.words)
            if flag := _segment_flag(segment, starts):
                flags.append(flag)
    return ArticulationReport(flags=tuple(flags), words_checked=checked)
