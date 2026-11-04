"""Word-level transcript shared by the speech, content and voice pipelines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    """One spoken word with its timing.

    `logprob` is the model's confidence for this word only, on a natural log
    scale. Providers that report confidence per segment (Groq Whisper) leave
    it as None instead of copying the segment value onto every word, so a
    caller must check for None.
    """

    text: str
    start_ms: int
    end_ms: int
    logprob: float | None = None


@dataclass(frozen=True)
class Segment:
    """A sentence or clause as the transcription model grouped it.

    `confidence` is the model's average log probability for the whole
    segment, or None if the provider gives none.
    """

    text: str
    start_ms: int
    end_ms: int
    words: tuple[Word, ...] = ()
    confidence: float | None = None


@dataclass(frozen=True)
class Transcript:
    """The transcription of one recording, segments in time order."""

    segments: tuple[Segment, ...]
    language: str = "en"

    @property
    def words(self) -> tuple[Word, ...]:
        return tuple(word for segment in self.segments for word in segment.words)

    @property
    def text(self) -> str:
        return " ".join(segment.text for segment in self.segments if segment.text)

    @property
    def duration_ms(self) -> int:
        return self.segments[-1].end_ms if self.segments else 0

    @property
    def is_empty(self) -> bool:
        return not any(segment.text for segment in self.segments)
