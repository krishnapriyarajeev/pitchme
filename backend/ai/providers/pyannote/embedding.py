"""Speaker embeddings with pyannote, for matching a voice to a sample.

Uses the diarization extra's own embedding model, so no second voice
library is needed. pyannote/embedding is gated like the diarization
models: the HF_TOKEN account must accept its licence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ai.diarize.base import DiarizeError

from .diarizer import load_pretrained

MODEL_NAME = "pyannote/embedding"


class PyannoteEmbedder:
    def __init__(self, hf_token: str | None = None, *, inference: Any = None) -> None:
        if inference is not None:
            self._inference = inference
            return
        if not hf_token:
            raise DiarizeError(
                f"HF_TOKEN is not set. Accept the {MODEL_NAME} licence on Hugging Face "
                "and set a read token."
            )
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

    def embed_span(self, path: str | Path, start_ms: int, end_ms: int) -> np.ndarray:
        from pyannote.core import Segment

        return np.asarray(self._inference.crop(str(path), Segment(start_ms / 1000, end_ms / 1000)))
