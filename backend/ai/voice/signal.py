"""The waveform every voice measure reads, and the windows it is cut into.

Audio is loaded as 16 kHz mono float samples in [-1, 1]. Measures are taken
for the whole talk and for overlapping 15 second windows, so a nervous
minute in a calm talk still shows.
"""

from __future__ import annotations

import tempfile
import wave
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import parselmouth

from ai.utils.audio import SAMPLE_RATE, extract_audio

ANALYSIS_WINDOW_S = 15.0
ANALYSIS_STEP_S = 10.0
# Shorter than this there is too little sound to measure.
MIN_DURATION_S = 1.0


@dataclass(frozen=True, eq=False)
class AudioSignal:
    samples: np.ndarray
    sample_rate: int

    @property
    def duration_s(self) -> float:
        return len(self.samples) / self.sample_rate

    def to_sound(self) -> parselmouth.Sound:
        return parselmouth.Sound(
            self.samples.astype(np.float64), sampling_frequency=self.sample_rate
        )


def windows(duration_s: float) -> Iterator[tuple[float, float]]:
    """(start, end) of each analysis window. A tail shorter than
    MIN_DURATION_S is dropped."""
    t = 0.0
    while t < duration_s:
        end = min(t + ANALYSIS_WINDOW_S, duration_s)
        if end - t < MIN_DURATION_S:
            return
        yield round(t, 2), round(end, 2)
        if end >= duration_s:
            return
        t += ANALYSIS_STEP_S


def _read_pcm16(path: Path) -> AudioSignal | None:
    """Read a 16 kHz mono 16-bit WAV directly, or None if it is anything else."""
    try:
        with wave.open(str(path)) as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (SAMPLE_RATE, 1, 2):
                return None
            frames = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError):
        return None
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    return AudioSignal(samples=samples, sample_rate=SAMPLE_RATE)


def load_audio(path: str | Path) -> AudioSignal:
    """Load any audio or video file as 16 kHz mono samples. Files that are
    not already in that format go through ffmpeg first."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Audio file not found: {source}")
    if source.suffix.lower() == ".wav" and (signal := _read_pcm16(source)):
        return signal
    with tempfile.TemporaryDirectory(prefix="pitchme-voice-") as tmp:
        wav_path = extract_audio(source, Path(tmp) / "audio.wav")
        signal = _read_pcm16(wav_path)
    if signal is None:  # pragma: no cover - extract_audio always writes this format
        raise ValueError(f"Could not read the converted audio of {source.name}")
    return signal
