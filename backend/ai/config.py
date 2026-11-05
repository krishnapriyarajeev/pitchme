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
    gemini_model: str = "gemini-3.8-flash"
    # Room for a long transcript judged against a full reference document.
    llm_max_output_tokens: int = 4096

    # ---- Transcription ----
    transcribe_provider: str = "groq"
    whisper_model: str = "whisper-large-v3-turbo"
    whisper_model_size: str = "base"
    # auto, cpu or cuda. Used only by the local provider.
    whisper_device: str = "auto"

    # ---- Diarization ----
    diarize_provider: str = "pyannote"
    # Read token for the gated pyannote models on Hugging Face.
    hf_token: SecretStr = SecretStr("")

    # ---- Voice cloning ----
    voice_clone_provider: str = "cartesia"
    cartesia_api_key: SecretStr = SecretStr("")
    # Emotion and speed only take effect on sonic-3 and later.
    cartesia_model: str = "sonic-3"
    cartesia_language: str = "en"
    resemble_api_key: SecretStr = SecretStr("")

    # ---- Live call (the LiveKit agent worker that plays the buyer) ----
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: SecretStr = SecretStr("")
    # Speech to text and text to speech for the buyer. The buyer thinks
    # with GROQ_MODEL, because a live call needs a fast reply.
    deepgram_api_key: SecretStr = SecretStr("")
    deepgram_stt_model: str = "nova-3"
    deepgram_tts_voice: str = "aura-2-andromeda-en"
    # A call ends on its own after this long, so a phone left in a pocket
    # does not keep the buyer talking.
    rehearsal_max_minutes: int = 20
    # The worker reports each finished call to the API at this address.
    server_public_base_url: str = "http://localhost:8000"
    ai_callback_key: SecretStr = SecretStr("")

    # ---- Vision ----
    # Folder with the MediaPipe .task models; empty means ai/models.
    vision_models_dir: str = ""


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()
