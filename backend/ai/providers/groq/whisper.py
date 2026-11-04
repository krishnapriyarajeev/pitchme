"""Groq's hosted Whisper as a TranscribeClient.

`verbose_json` with word and segment timestamps gives two flat lists, words
and segments, with no link between them. Words are put back into segments
by time. Groq reports confidence per segment only (`avg_logprob`), so every
Word keeps `logprob=None`.

Free tier for whisper-large-v3-turbo: 20 requests a minute and 8 hours of
audio a day.
"""

from __future__ import annotations

from bisect import bisect_right
from pathlib import Path
from typing import Any

from ai.core.transcript import Segment, Transcript, Word
from ai.transcribe.base import TranscribeClient, TranscribeError, require_file, seconds_to_ms

from .llm import KEY_HELP

DEFAULT_MODEL = "whisper-large-v3-turbo"


def _group_words(segments: list[dict], words: list[dict]) -> list[list[dict]]:
    """Each word goes to the last segment that starts at or before it.

    This keeps words that fall in a pause between segments, or exactly on a
    boundary, instead of dropping them.
    """
    starts = [segment["start"] for segment in segments]
    groups: list[list[dict]] = [[] for _ in segments]
    for word in words:
        groups[max(0, bisect_right(starts, word["start"]) - 1)].append(word)
    return groups


def parse_verbose_json(data: dict[str, Any]) -> Transcript:
    language = data.get("language") or "en"
    segments = data.get("segments") or []
    if not (data.get("text") or "").strip() or not segments:
        return Transcript(segments=(), language=language)

    groups = _group_words(segments, data.get("words") or [])
    return Transcript(
        segments=tuple(
            Segment(
                text=segment["text"].strip(),
                start_ms=seconds_to_ms(segment["start"]),
                end_ms=seconds_to_ms(segment["end"]),
                words=tuple(
                    Word(
                        text=word["word"].strip(),
                        start_ms=seconds_to_ms(word["start"]),
                        end_ms=seconds_to_ms(word["end"]),
                    )
                    for word in group
                ),
                confidence=segment.get("avg_logprob"),
            )
            for segment, group in zip(segments, groups, strict=True)
        ),
        language=language,
    )


class GroqWhisperClient(TranscribeClient):
    def __init__(
        self, api_key: str | None = None, model: str = DEFAULT_MODEL, *, client: Any = None
    ) -> None:
        if client is None:
            if not api_key:
                raise TranscribeError(KEY_HELP)
            from groq import Groq

            client = Groq(api_key=api_key)
        self._client = client
        self.model = model

    def transcribe(self, audio_path: str | Path) -> Transcript:
        path = require_file(audio_path)
        try:
            with path.open("rb") as audio:
                response = self._client.audio.transcriptions.create(
                    model=self.model,
                    file=(path.name, audio),
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"],
                )
        except Exception as exc:
            raise TranscribeError(f"Groq transcription failed for {path.name}: {exc}") from exc
        data = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        return parse_verbose_json(data)
