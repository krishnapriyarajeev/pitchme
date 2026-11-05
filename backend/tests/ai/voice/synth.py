"""Synthetic voices with known properties, so every voice measure can be
checked against a value we chose instead of a recording."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from ai.voice.signal import AudioSignal

SR = 16_000


def _rng(seed: int = 7) -> np.random.Generator:
    return np.random.default_rng(seed)


def tone(seconds: float, hz: float = 150.0, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    return (amplitude * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def glide(seconds: float, start_hz: float, end_hz: float, amplitude: float = 0.5) -> np.ndarray:
    """A pitch that moves smoothly (on a log scale) from start_hz to end_hz."""
    n = int(seconds * SR)
    hz = start_hz * (end_hz / start_hz) ** (np.arange(n) / n)
    phase = 2 * np.pi * np.cumsum(hz) / SR
    return (amplitude * np.sin(phase)).astype(np.float32)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def cycles(
    seconds: float,
    hz: float = 150.0,
    *,
    period_jitter: float = 0.0,
    amplitude_jitter: float = 0.0,
    amplitude: float = 0.5,
    seed: int = 7,
) -> np.ndarray:
    """A voice built one glottal cycle at a time, with each cycle's length
    and loudness varied at random by up to the given share. This is what
    jitter and shimmer measure."""
    rng = _rng(seed)
    out: list[np.ndarray] = []
    total = 0
    target = int(seconds * SR)
    harmonics = np.array([1.0, 0.5, 0.25])
    while total < target:
        period = (SR / hz) * (1 + rng.uniform(-period_jitter, period_jitter))
        gain = amplitude * (1 + rng.uniform(-amplitude_jitter, amplitude_jitter))
        n = max(2, round(period))
        phase = 2 * np.pi * np.arange(n) / n
        cycle = sum(h * np.sin((k + 1) * phase) for k, h in enumerate(harmonics))
        out.append(gain * cycle / harmonics.sum())
        total += n
    return np.concatenate(out)[:target].astype(np.float32)


def noisy(samples: np.ndarray, noise: float, seed: int = 7) -> np.ndarray:
    return (samples + _rng(seed).normal(0, noise, len(samples))).astype(np.float32)


def syllables(seconds: float, per_second: float, hz: float = 150.0) -> np.ndarray:
    """A voiced tone switched on and off `per_second` times a second, each
    burst shaped like a syllable."""
    period = int(SR / per_second)
    on = int(period * 0.6)
    envelope = np.zeros(period, dtype=np.float32)
    envelope[:on] = np.hanning(on)
    count = int(seconds * per_second)
    shape = np.tile(envelope, count)
    return (shape * tone(len(shape) / SR, hz, 0.6)).astype(np.float32)


def signal(*parts: np.ndarray) -> AudioSignal:
    return AudioSignal(samples=np.concatenate(parts), sample_rate=SR)


def write_wav(path: Path, samples: np.ndarray, rate: int = SR, channels: int = 1) -> Path:
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    if channels > 1:
        pcm = np.repeat(pcm[:, None], channels, axis=1)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return path
