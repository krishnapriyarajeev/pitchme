"""Loudness from RMS energy, in dB relative to full scale.

Only frames with sound in them count. Pauses are far quieter than speech,
so including them would make every talk look dynamic and every pause look
like a drop in volume.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .signal import AudioSignal, windows

FRAME_LENGTH = 2048
HOP_LENGTH = 512
FLOOR_DB = -100.0

# A frame is speech when it is within this many dB of the loud end of the
# talk (its 95th percentile).
ACTIVE_RANGE_DB = 35.0

# A window that is mostly pause is not judged for volume.
MIN_ACTIVE_SHARE = 0.25


@dataclass(frozen=True)
class LoudnessWindow:
    t_start_s: float
    t_end_s: float
    mean_db: float
    std_db: float


@dataclass(frozen=True)
class LoudnessReport:
    mean_db: float
    std_db: float
    min_db: float
    max_db: float
    # Share of frames loud enough to count as speech.
    active_fraction: float
    times_s: tuple[float, ...]
    db: tuple[float, ...]
    windows: tuple[LoudnessWindow, ...] = ()


def rms_db(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    """Frame times (centres) and RMS level in dBFS."""
    if samples.size < FRAME_LENGTH:
        samples = np.pad(samples, (0, FRAME_LENGTH - samples.size))
    frames = np.lib.stride_tricks.sliding_window_view(samples, FRAME_LENGTH)[::HOP_LENGTH]
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    db = np.maximum(20 * np.log10(np.maximum(rms, 1e-10)), FLOOR_DB)
    times = (np.arange(len(db)) * HOP_LENGTH + FRAME_LENGTH / 2) / sample_rate
    return times, db


def analyze_loudness(signal: AudioSignal) -> LoudnessReport:
    times, db = rms_db(signal.samples, signal.sample_rate)
    loud_end = np.percentile(db, 95)
    active = (db >= loud_end - ACTIVE_RANGE_DB) & (db > FLOOR_DB)
    contour = (tuple(round(float(t), 3) for t in times), tuple(round(float(d), 1) for d in db))
    if not active.any():
        return LoudnessReport(FLOOR_DB, 0.0, FLOOR_DB, FLOOR_DB, 0.0, *contour)

    speech = db[active]
    report_windows = []
    for start, end in windows(signal.duration_s):
        inside = (times >= start) & (times < end)
        part = db[inside & active]
        if not inside.any() or part.size < MIN_ACTIVE_SHARE * inside.sum():
            continue
        report_windows.append(
            LoudnessWindow(start, end, round(float(part.mean()), 1), round(float(part.std()), 1))
        )

    return LoudnessReport(
        mean_db=round(float(speech.mean()), 1),
        std_db=round(float(speech.std()), 1),
        min_db=round(float(speech.min()), 1),
        max_db=round(float(speech.max()), 1),
        active_fraction=round(float(active.mean()), 3),
        times_s=contour[0],
        db=contour[1],
        windows=tuple(report_windows),
    )
