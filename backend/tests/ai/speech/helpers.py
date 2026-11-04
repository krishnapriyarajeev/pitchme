"""Small builders for speech tests: transcripts with exact timing and an
LLM that replies with a fixed object."""

from __future__ import annotations

from typing import Any

from ai.core.llm import LLMClient
from ai.core.transcript import Segment, Transcript, Word


class FakeLLM(LLMClient):
    def __init__(self, reply: dict[str, Any] | None = None) -> None:
        self.reply = reply if reply is not None else {"fillers": [], "summary": "No fillers."}
        self.prompts: list[str] = []

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        raise AssertionError("speech only uses complete_json")

    def complete_json(
        self, prompt: str, *, schema: dict[str, Any], system: str | None = None
    ) -> dict[str, Any]:
        self.prompts.append(prompt)
        return self.reply


def steady_words(
    count: int,
    *,
    every_ms: int = 400,
    length_ms: int = 300,
    start_ms: int = 0,
    text: str = "word",
    logprob: float | None = None,
) -> list[Word]:
    """`count` words, one every `every_ms` (400 ms is 150 wpm)."""
    return [
        Word(text, start_ms + i * every_ms, start_ms + i * every_ms + length_ms, logprob)
        for i in range(count)
    ]


def transcript_of(
    words: list[Word], *, confidence: float | None = None, per_segment: int = 0
) -> Transcript:
    """Group words into segments of `per_segment` (all in one by default)."""
    if not words:
        return Transcript(segments=())
    size = per_segment or len(words)
    segments = []
    for i in range(0, len(words), size):
        chunk = tuple(words[i : i + size])
        segments.append(
            Segment(
                text=" ".join(w.text for w in chunk),
                start_ms=chunk[0].start_ms,
                end_ms=chunk[-1].end_ms,
                words=chunk,
                confidence=confidence,
            )
        )
    return Transcript(segments=tuple(segments))
