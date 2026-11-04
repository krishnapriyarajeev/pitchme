"""Speaking rate in syllables per second, from the sound alone.

Each syllable has a vowel at its centre, and the vowel is a voiced peak in
loudness. A peak counts as a new syllable when loudness dips by at least
MIN_DIP_DB between it and the previous one (after de Jong and Wempe, 2009).
This needs no transcript, so it also works where transcription fails.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .pitch import PitchReport, analyze_pitch
from .signal import AudioSignal, windows

INTENSITY_MIN_PITCH_HZ = 50
INTENSITY_STEP_S = 0.01
# Peaks quieter than this far below the loudest part are background.
SILENCE_RANGE_DB = 25.0
# Two peaks with less of a dip between them belong to one syllable.
MIN_DIP_DB = 2.0


@dataclass(frozen=True)
class RateWindow:
    t_start_s: float
    t_end_s: float
    syllables_per_s: float


@dataclass(frozen=True)
class SpeakingRateReport:
    global_sps: float
    syllable_count: int = 0
    windows: tuple[RateWindow, ...] = ()


def _local_peaks(values: np.ndarray) -> np.ndarray:
    inner = (values[1:-1] > values[:-2]) & (values[1:-1] >= values[2:])
    return np.flatnonzero(inner) + 1


def syllable_times(signal: AudioSignal, pitch: PitchReport | None = None) -> np.ndarray:
    """Times in seconds of each syllable centre found."""
    # Praat needs 6.4 periods of the lowest pitch to measure loudness.
    if signal.duration_s < 6.4 / INTENSITY_MIN_PITCH_HZ:
        return np.array([])
    intensity = signal.to_sound().to_intensity(
        minimum_pitch=INTENSITY_MIN_PITCH_HZ, time_step=INTENSITY_STEP_S
    )
    values = np.nan_to_num(np.asarray(intensity.values).ravel(), nan=-300.0)
    times = np.asarray(intensity.xs())

    threshold = max(float(np.median(values)), float(np.percentile(values, 99)) - SILENCE_RANGE_DB)
    kept: list[int] = []
    for i in _local_peaks(values):
        if values[i] <= threshold:
            continue
        if not kept:
            kept.append(i)
            continue
        prev = kept[-1]
        dip = values[prev : i + 1].min()
        if values[i] - dip >= MIN_DIP_DB and values[prev] - dip >= MIN_DIP_DB:
            kept.append(i)
        elif values[i] > values[prev]:
            kept[-1] = i  # same syllable, louder centre

    pitch = pitch or analyze_pitch(signal)
    pitch_times = np.asarray(pitch.times_s)
    pitch_hz = np.asarray(pitch.hz)
    if pitch_times.size == 0:
        return np.array([])
    peak_times = times[kept]
    nearest = np.clip(np.searchsorted(pitch_times, peak_times), 0, pitch_times.size - 1)
    return peak_times[pitch_hz[nearest] > 0]


def analyze_rate(signal: AudioSignal, pitch: PitchReport | None = None) -> SpeakingRateReport:
    if signal.duration_s <= 0:
        return SpeakingRateReport(global_sps=0.0)
    found = syllable_times(signal, pitch)
    report_windows = tuple(
        RateWindow(
            start,
            end,
            round(int(((found >= start) & (found < end)).sum()) / (end - start), 2),
        )
        for start, end in windows(signal.duration_s)
    )
    return SpeakingRateReport(
        global_sps=round(found.size / signal.duration_s, 2),
        syllable_count=int(found.size),
        windows=report_windows,
    )
