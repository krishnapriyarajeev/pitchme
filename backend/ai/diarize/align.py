"""Give each transcript word the speaker who was talking at that moment.

Transcription and diarization are timed by two separate models, so their
edges never quite agree. A word is placed by its midpoint, which is more
stable than its start. When segments overlap (a "mm-hmm" inside the other
person's turn), the shortest segment wins: it is the more specific claim.
A word that falls in a short gap between segments takes the nearest
segment within MAX_GAP_MS; past that it stays unassigned.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai.core.transcript import Transcript

from .base import DiarizedSegment

MAX_GAP_MS = 1_000


@dataclass(frozen=True)
class TaggedWord:
    index: int  # position in transcript.words
    text: str
    start_ms: int
    end_ms: int
    speaker: str | None


@dataclass(frozen=True)
class Turn:
    """Consecutive words by one speaker."""

    speaker: str | None
    words: tuple[TaggedWord, ...]

    @property
    def start_ms(self) -> int:
        return self.words[0].start_ms

    @property
    def end_ms(self) -> int:
        return self.words[-1].end_ms

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass(frozen=True)
class TaggedTranscript:
    transcript: Transcript
    words: tuple[TaggedWord, ...]

    @property
    def speakers(self) -> tuple[str, ...]:
        return tuple(sorted({w.speaker for w in self.words if w.speaker}))

    def turns(self) -> tuple[Turn, ...]:
        """Runs of words by one speaker. An unassigned word joins the turn
        it sits in, so a labelling gap does not split a sentence."""
        turns: list[list[TaggedWord]] = []
        current: str | None = None
        for word in self.words:
            speaker = word.speaker or current
            if turns and speaker == current:
                turns[-1].append(word)
            else:
                turns.append([word])
                current = speaker
        return tuple(Turn(_turn_speaker(run), tuple(run)) for run in turns)


def _turn_speaker(words: list[TaggedWord]) -> str | None:
    return next((w.speaker for w in words if w.speaker), None)


def speaker_at(t_ms: int, segments: tuple[DiarizedSegment, ...]) -> str | None:
    covering = [s for s in segments if s.start_ms <= t_ms < s.end_ms]
    if covering:
        return min(covering, key=lambda s: s.duration_ms).speaker
    nearest = min(
        segments,
        key=lambda s: min(abs(t_ms - s.start_ms), abs(t_ms - s.end_ms)),
        default=None,
    )
    if nearest is None:
        return None
    gap = min(abs(t_ms - nearest.start_ms), abs(t_ms - nearest.end_ms))
    return nearest.speaker if gap <= MAX_GAP_MS else None


def tag_speakers(transcript: Transcript, segments: tuple[DiarizedSegment, ...]) -> TaggedTranscript:
    return TaggedTranscript(
        transcript=transcript,
        words=tuple(
            TaggedWord(
                i, w.text, w.start_ms, w.end_ms, speaker_at((w.start_ms + w.end_ms) // 2, segments)
            )
            for i, w in enumerate(transcript.words)
        ),
    )
