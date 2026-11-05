"""Cartesia voice cloning and speech.

Instant cloning from a 10-30 s sample, and per-clip emotion and speed. Those
two only work on sonic-3 and later; on an older model they are ignored.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai.voice_cloning.base import ProsodyParams, VoiceCloneClient, VoiceCloneError, VoiceSample

DEFAULT_MODEL = "sonic-3"
OUTPUT_FORMAT = {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 16_000}
KEY_HELP = "Set CARTESIA_API_KEY (https://play.cartesia.ai/keys)."


class CartesiaVoiceClient(VoiceCloneClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        language: str = "en",
        *,
        client: Any = None,
    ) -> None:
        if client is None:
            if not api_key:
                raise VoiceCloneError(f"CARTESIA_API_KEY is not set. {KEY_HELP}")
            from cartesia import Cartesia

            client = Cartesia(api_key=api_key)
        self._client = client
        self.model = model
        self.language = language

    def clone_voice(self, sample: VoiceSample, name: str) -> str:
        path = Path(sample.audio_path)
        try:
            with path.open("rb") as clip:
                voice = self._client.voices.clone(
                    clip=(path.name, clip), name=name, language=self.language
                )
        except OSError as exc:
            raise VoiceCloneError(f"Could not read voice sample {path}: {exc}") from exc
        except Exception as exc:
            raise VoiceCloneError(f"Cartesia clone failed: {exc}") from exc
        return voice.id

    def synthesize(self, text: str, voice_id: str, prosody: ProsodyParams) -> bytes:
        config: dict[str, Any] = {"speed": prosody.speed}
        if prosody.emotion != "neutral":
            config["emotion"] = prosody.emotion
        try:
            response = self._client.tts.generate(
                model_id=self.model,
                transcript=text,
                voice={"mode": "id", "id": voice_id},
                output_format=OUTPUT_FORMAT,
                language=self.language,
                generation_config=config,
            )
            return response.read()
        except Exception as exc:
            raise VoiceCloneError(f"Cartesia speech failed: {exc}") from exc

    def delete_voice(self, voice_id: str) -> None:
        try:
            self._client.voices.delete(voice_id)
        except Exception as exc:
            raise VoiceCloneError(f"Cartesia could not delete voice {voice_id}: {exc}") from exc
