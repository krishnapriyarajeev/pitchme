"""Speaker embeddings with pyannote, for matching a voice to a sample.

Uses WeSpeaker, the embedding model inside pyannote's own diarization
pipeline, so it needs no licence beyond the diarization ones. (The older
pyannote/embedding model is gated separately.)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ai.diarize.base import DiarizeError

from .diarizer import load_pretrained

MODEL_NAME = "pyannote/wespeaker-voxceleb-resnet34-LM"


class PyannoteEmbedder:
    def __init__(
        self, hf_token: str | None = None, *, inference: Any = None, audio: Any = None
    ) -> None:
        # Reads file durations; pyannote.audio.Audio unless one is passed in.
        self._audio = audio
        self._durations: dict[str, float] = {}
        if inference is not None:
            self._inference = inference
            return
        if not hf_token:
            raise DiarizeError("HF_TOKEN is not set. Set a Hugging Face read token.")
        try:
            from pyannote.audio import Inference, Model
        except ImportError as exc:
            raise DiarizeError(
                "pyannote.audio is not installed. Run: uv sync --extra diarize"
            ) from exc
        try:
            model = load_pretrained(Model, MODEL_NAME, hf_token)
        except Exception as exc:  # pragma: no cover - needs the network and the licence
            raise DiarizeError(f"Could not load {MODEL_NAME}: {exc}") from exc
        self._inference = Inference(model, window="whole")

    def embed_file(self, path: str | Path) -> np.ndarray:
        return np.asarray(self._inference(str(path)))

    def _duration(self, path: str) -> float:
        if path not in self._durations:
            if self._audio is None:
                from pyannote.audio import Audio

                self._audio = Audio()
            self._durations[path] = float(self._audio.get_duration(path))
        return self._durations[path]

    def embed_span(self, path: str | Path, start_ms: int, end_ms: int) -> np.ndarray:
        """Embedding of one stretch. Diarization rounds segment ends, so the
        last one can end a few ms after the file does; the span is clamped
        to the file, or pyannote refuses the crop."""
        from pyannote.core import Segment

        name = str(path)
        end_s = min(end_ms / 1000, self._duration(name))
        return np.asarray(self._inference.crop(name, Segment(start_ms / 1000, end_s)))
