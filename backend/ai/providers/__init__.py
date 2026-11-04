"""The one place that knows every provider by name.

Pipelines ask for "the configured LLM" or "the configured transcriber" and
get back an `LLMClient` or `TranscribeClient`. Adding a provider means one
new branch here and no change to any pipeline.
"""

from __future__ import annotations

from functools import lru_cache

from ai.config import AISettings, get_ai_settings
from ai.core.llm import LLMClient, LLMError
from ai.transcribe.base import TranscribeClient, TranscribeError

LLM_PROVIDERS = ("groq", "gemini")
TRANSCRIBE_PROVIDERS = ("groq", "local")


def make_llm_client(settings: AISettings) -> LLMClient:
    provider = settings.llm_provider.strip().lower()
    if provider == "groq":
        from .groq.llm import GroqClient

        return GroqClient(
            settings.groq_api_key.get_secret_value(),
            settings.groq_model,
            max_output_tokens=settings.llm_max_output_tokens,
        )
    if provider == "gemini":
        from .gemini.llm import GeminiClient

        return GeminiClient(
            settings.gemini_api_key.get_secret_value(),
            settings.gemini_model,
            max_output_tokens=settings.llm_max_output_tokens,
        )
    raise LLMError(f"Unknown LLM_PROVIDER {provider!r}. Use one of: {', '.join(LLM_PROVIDERS)}")


def make_transcribe_client(settings: AISettings) -> TranscribeClient:
    provider = settings.transcribe_provider.strip().lower()
    if provider == "groq":
        from .groq.whisper import GroqWhisperClient

        return GroqWhisperClient(settings.groq_api_key.get_secret_value(), settings.whisper_model)
    if provider == "local":
        from .local.whisper import LocalWhisperClient

        return LocalWhisperClient(settings.whisper_model_size, settings.whisper_device)
    raise TranscribeError(
        f"Unknown TRANSCRIBE_PROVIDER {provider!r}. Use one of: {', '.join(TRANSCRIBE_PROVIDERS)}"
    )


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """The process-wide LLM client chosen by LLM_PROVIDER (default groq)."""
    return make_llm_client(get_ai_settings())


@lru_cache(maxsize=1)
def get_transcribe_client() -> TranscribeClient:
    """The process-wide transcriber chosen by TRANSCRIBE_PROVIDER (default groq)."""
    return make_transcribe_client(get_ai_settings())


__all__ = [
    "get_llm_client",
    "get_transcribe_client",
    "make_llm_client",
    "make_transcribe_client",
]
