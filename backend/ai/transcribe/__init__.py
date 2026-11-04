"""Audio to transcript. Providers live in `ai/providers/`; get one with
`ai.providers.get_transcribe_client()`."""

from .base import TranscribeClient, TranscribeError

__all__ = ["TranscribeClient", "TranscribeError"]
