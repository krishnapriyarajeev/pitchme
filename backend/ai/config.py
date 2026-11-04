"""Provider settings for the AI layer.

Read from the environment and `.env`, the same file the server uses. The AI
layer keeps its own settings so it never imports `server`: a script, a test
or the LiveKit worker can use it without the API's database and auth config.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- LLM ----
    llm_provider: str = "groq"
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "openai/gpt-oss-20b"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.0-flash"
    # Room for a long transcript judged against a full reference document.
    llm_max_output_tokens: int = 4096

    # ---- Transcription ----
    transcribe_provider: str = "groq"
    whisper_model: str = "whisper-large-v3-turbo"
    whisper_model_size: str = "base"
    # auto, cpu or cuda. Used only by the local provider.
    whisper_device: str = "auto"


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()
