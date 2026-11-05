"""Diarization with pyannote.audio, run locally.

Needs the `diarize` extra and a Hugging Face read token (HF_TOKEN) whose
account has accepted the licences of pyannote/speaker-diarization-3.1 and
pyannote/segmentation-3.0. The first call downloads the models (a few
hundred MB) into the Hugging Face cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai.diarize.base import DiarizeClient, DiarizedSegment, DiarizeError

MODEL_NAME = "pyannote/speaker-diarization-3.1"
TOKEN_HELP = (
    "Set HF_TOKEN to a Hugging Face read token whose account accepted the "
    f"{MODEL_NAME} and pyannote/segmentation-3.0 licences."
)


def load_pretrained(loader: Any, name: str, token: str) -> Any:
    """`from_pretrained` with the token argument of pyannote 4 (token) or
    pyannote 3 (use_auth_token)."""
    try:
        return loader.from_pretrained(name, token=token)
    except TypeError:
        return loader.from_pretrained(name, use_auth_token=token)


class PyannoteDiarizer(DiarizeClient):
    def __init__(self, hf_token: str | None = None, *, pipeline: Any = None) -> None:
        if pipeline is not None:
            self._pipeline = pipeline
            return
        if not hf_token:
            raise DiarizeError(f"HF_TOKEN is not set. {TOKEN_HELP}")
        try:
            from pyannote.audio import Pipeline
        except ImportError as exc:
            raise DiarizeError(
                "pyannote.audio is not installed. Run: uv sync --extra diarize"
            ) from exc
        try:
            self._pipeline = load_pretrained(Pipeline, MODEL_NAME, hf_token)
        except Exception as exc:  # pragma: no cover - needs the network and the licence
            raise DiarizeError(f"Could not load {MODEL_NAME}: {exc}") from exc
        if self._pipeline is None:  # pragma: no cover - pyannote returns None without access
            raise DiarizeError(f"{MODEL_NAME} did not load. {TOKEN_HELP}")

    def diarize(
        self, audio_path: str | Path, min_speakers: int = 1, max_speakers: int = 2
    ) -> tuple[DiarizedSegment, ...]:
        path = Path(audio_path)
        if not path.is_file():
            raise DiarizeError(f"Audio file not found: {path}")
        try:
            result = self._pipeline(str(path), min_speakers=min_speakers, max_speakers=max_speakers)
        except Exception as exc:
            raise DiarizeError(f"Diarization failed for {path.name}: {exc}") from exc

        # pyannote 4 wraps the annotation; pyannote 3 returns it directly.
        annotation = getattr(result, "speaker_diarization", result)
        segments = sorted(
            (
                DiarizedSegment(speaker, round(turn.start * 1000), round(turn.end * 1000))
                for turn, _, speaker in annotation.itertracks(yield_label=True)
            ),
            key=lambda s: (s.start_ms, s.end_ms),
        )
        return tuple(s for s in segments if s.end_ms > s.start_ms)
