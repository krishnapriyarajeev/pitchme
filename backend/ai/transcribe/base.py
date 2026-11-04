"""The transcription contract.

Only the code that produces a transcript needs this. The speech and content
pipelines receive a finished `Transcript` and never call a provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ai.core.transcript import Transcript


class TranscribeError(RuntimeError):
    """Audio could not be transcribed."""


class TranscribeClient(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str | Path) -> Transcript:
        """Transcribe one audio file with word and segment timing.

        Returns an empty transcript when the audio holds no speech. Raises
        TranscribeError when the file is missing or the provider fails.
        """


def require_file(audio_path: str | Path) -> Path:
    path = Path(audio_path)
    if not path.is_file():
        raise TranscribeError(f"Audio file not found: {path}")
    return path


def seconds_to_ms(seconds: float) -> int:
    return round(seconds * 1000)
