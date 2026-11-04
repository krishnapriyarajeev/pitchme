"""faster-whisper as a TranscribeClient. Needs the `whisper-local` extra.

No key and no rate limit. Speed depends on the machine: `base` is fine on a
CPU, `large-v3` wants a GPU. Unlike Groq, it gives a real confidence for
each word. faster-whisper reports it as a 0-1 probability; it is stored as a
natural log so it matches the log scale of segment confidence.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ai.core.transcript import Segment, Transcript, Word
from ai.transcribe.base import TranscribeClient, TranscribeError, require_file, seconds_to_ms

DEFAULT_MODEL_SIZE = "base"

# log(0) is undefined; "the model was completely unsure" is still a result.
_MIN_PROBABILITY = 1e-8


def probability_to_logprob(probability: float) -> float:
    return math.log(max(probability, _MIN_PROBABILITY))


def build_segment(raw: Any) -> Segment:
    return Segment(
        text=raw.text.strip(),
        start_ms=seconds_to_ms(raw.start),
        end_ms=seconds_to_ms(raw.end),
        words=tuple(
            Word(
                text=word.word.strip(),
                start_ms=seconds_to_ms(word.start),
                end_ms=seconds_to_ms(word.end),
                logprob=probability_to_logprob(word.probability),
            )
            for word in raw.words or ()
        ),
        confidence=raw.avg_logprob,
    )


class LocalWhisperClient(TranscribeClient):
    def __init__(
        self, model_size: str = DEFAULT_MODEL_SIZE, device: str = "auto", *, model: Any = None
    ) -> None:
        if model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise TranscribeError(
                    "faster-whisper is not installed: uv sync --extra whisper-local"
                ) from exc
            try:
                model = WhisperModel(model_size, device=device)
            except Exception as exc:  # pragma: no cover - depends on the machine
                raise TranscribeError(
                    f"Could not load whisper model {model_size!r}: {exc}"
                ) from exc
        self._model = model

    def transcribe(self, audio_path: str | Path) -> Transcript:
        path = require_file(audio_path)
        try:
            raw_segments, info = self._model.transcribe(str(path), word_timestamps=True)
            # A lazy generator: the real work happens while it is read.
            segments = tuple(build_segment(raw) for raw in raw_segments)
        except Exception as exc:
            raise TranscribeError(f"Local transcription failed for {path.name}: {exc}") from exc
        return Transcript(segments=segments, language=info.language)
