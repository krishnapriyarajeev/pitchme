"""A voice clone client that speaks in tones, for tests."""

from __future__ import annotations

import math
import struct

from ai.voice_cloning.base import ProsodyParams, VoiceCloneClient, VoiceSample
from ai.voice_cloning.wav import Pcm, write_wav

RATE = 16_000


def tone_wav(ms: int, rate: int = RATE, level: int = 8000) -> bytes:
    count = rate * ms // 1000
    frames = b"".join(
        struct.pack("<h", int(level * math.sin(2 * math.pi * 220 * i / rate))) for i in range(count)
    )
    return write_wav(Pcm(frames, rate, 1, 2))


class FakeVoiceClient(VoiceCloneClient):
    """Each word becomes 100 ms of tone."""

    def __init__(self) -> None:
        self.cloned: list[tuple[VoiceSample, str]] = []
        self.spoken: list[tuple[str, str, ProsodyParams]] = []
        self.deleted: list[str] = []

    def clone_voice(self, sample: VoiceSample, name: str) -> str:
        self.cloned.append((sample, name))
        return f"voice-{len(self.cloned)}"

    def synthesize(self, text: str, voice_id: str, prosody: ProsodyParams) -> bytes:
        self.spoken.append((text, voice_id, prosody))
        return tone_wav(100 * len(text.split()))

    def delete_voice(self, voice_id: str) -> None:
        self.deleted.append(voice_id)
