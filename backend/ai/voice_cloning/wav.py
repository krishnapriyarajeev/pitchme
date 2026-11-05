"""Join WAV clips into one file, with silence between them.

Every provider returns a complete WAV file per clip, header included, so
clips cannot simply be concatenated: the result would be one header
followed by data with stray headers inside it.
"""

from __future__ import annotations

import io
import wave
from collections.abc import Sequence
from dataclasses import dataclass

from .base import VoiceCloneError


@dataclass(frozen=True)
class Pcm:
    frames: bytes
    rate: int
    channels: int
    width: int

    @property
    def duration_ms(self) -> int:
        bytes_per_ms = self.rate * self.channels * self.width / 1000
        return round(len(self.frames) / bytes_per_ms) if bytes_per_ms else 0


def read_wav(data: bytes) -> Pcm:
    try:
        with wave.open(io.BytesIO(data)) as wav:
            return Pcm(
                wav.readframes(wav.getnframes()),
                wav.getframerate(),
                wav.getnchannels(),
                wav.getsampwidth(),
            )
    except (wave.Error, EOFError) as exc:
        raise VoiceCloneError(f"Provider returned audio that is not a WAV file: {exc}") from exc


def write_wav(pcm: Pcm) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(pcm.channels)
        wav.setsampwidth(pcm.width)
        wav.setframerate(pcm.rate)
        wav.writeframes(pcm.frames)
    return out.getvalue()


def silence(ms: int, like: Pcm) -> bytes:
    frames = round(like.rate * ms / 1000)
    return b"\x00" * frames * like.channels * like.width


def join_wav(clips: Sequence[bytes], pauses_ms: Sequence[int] = ()) -> bytes:
    """One WAV of every clip in order, each followed by its pause (the
    pause after the last clip is kept, so a caller can add a tail)."""
    if not clips:
        raise VoiceCloneError("No audio clips to join")
    parts = [read_wav(c) for c in clips]
    first = parts[0]
    fmt = (first.rate, first.channels, first.width)
    for part in parts[1:]:
        if (part.rate, part.channels, part.width) != fmt:
            raise VoiceCloneError(
                f"Clips differ in format: {(part.rate, part.channels, part.width)} vs {fmt}"
            )
    pauses = list(pauses_ms) + [0] * (len(parts) - len(pauses_ms))
    frames = b"".join(
        p.frames + silence(pause, first) for p, pause in zip(parts, pauses, strict=False)
    )
    return write_wav(Pcm(frames, *fmt))
