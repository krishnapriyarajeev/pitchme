"""The voice-cloning interface every provider implements.

Clone quality differs a lot between vendors, so swapping one must be cheap:
code asks `ai.providers.get_voice_clone_client()` for a client and never
names a provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


class VoiceCloneError(RuntimeError):
    """A clone or speech call failed, or returned something unusable."""


# Delivery moods the rewrite step may ask for. Each provider maps these onto
# its own settings; one with no emotion control ignores them.
EMOTIONS = (
    "neutral",
    "confident",
    "calm",
    "enthusiastic",
    "curious",
    "sympathetic",
    "determined",
)
MIN_SPEED = 0.6
MAX_SPEED = 1.5


@dataclass(frozen=True)
class ProsodyParams:
    emotion: str = "neutral"
    speed: float = 1.0
    # Silence after this piece of speech, added when clips are joined.
    pause_after_ms: int = 0

    def __post_init__(self) -> None:
        if self.emotion not in EMOTIONS:
            object.__setattr__(self, "emotion", "neutral")
        object.__setattr__(self, "speed", max(MIN_SPEED, min(MAX_SPEED, float(self.speed))))
        object.__setattr__(self, "pause_after_ms", max(0, int(self.pause_after_ms)))


@dataclass(frozen=True)
class VoiceSample:
    """A clean recording of the user's voice (about 10-60 s).

    Cartesia needs only the audio. Resemble also needs a transcript of it
    and a link to a recording of the speaker consenting to the clone.
    """

    audio_path: str | Path
    transcript: str = ""
    consent_url: str = ""


class VoiceCloneClient(ABC):
    @abstractmethod
    def clone_voice(self, sample: VoiceSample, name: str) -> str:
        """Create a voice from the sample; returns the provider's voice id."""

    @abstractmethod
    def synthesize(self, text: str, voice_id: str, prosody: ProsodyParams) -> bytes:
        """`text` spoken in the voice, as 16 kHz mono 16-bit WAV bytes."""

    @abstractmethod
    def delete_voice(self, voice_id: str) -> None:
        """Remove a voice that is no longer used, for example after the user
        records a new sample."""
