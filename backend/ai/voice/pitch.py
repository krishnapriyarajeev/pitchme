"""Pitch (F0) and intonation, measured with Praat.

Range is the spread between the 5th and 95th percentile of pitch, not the
lowest and highest frame. A single octave error by the tracker would
otherwise make a flat voice look expressive.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .signal import AudioSignal, windows

PITCH_FLOOR_HZ = 75
PITCH_CEILING_HZ = 500
TIME_STEP_S = 0.01

# Intonation is judged over short stretches of voiced speech.
STRETCH_S = 2.0
# A stretch needs this many voiced frames (0.4 s) to judge.
STRETCH_MIN_FRAMES = 40
# A stretch whose pitch moves less than this is flat.
FLAT_STRETCH_SEMITONES = 2.0


@dataclass(frozen=True)
class PitchWindow:
    t_start_s: float
    t_end_s: float
    mean_hz: float
    std_hz: float
    range_semitones: float


@dataclass(frozen=True)
class PitchReport:
    mean_hz: float
    std_hz: float
    min_hz: float
    max_hz: float
    range_semitones: float
    voiced_fraction: float
    # One value per 10 ms frame; 0 where the frame was not voiced.
    times_s: tuple[float, ...]
    hz: tuple[float, ...]
    windows: tuple[PitchWindow, ...] = ()


@dataclass(frozen=True)
class IntonationReport:
    pitch_range_semitones: float
    # Share of 2 second stretches of speech where pitch barely moved.
    monotone_fraction: float
    # Mean speed of pitch movement inside voiced runs, in semitones a second.
    pitch_slope_mean: float


def semitones(high_hz: float, low_hz: float) -> float:
    if high_hz <= 0 or low_hz <= 0:
        return 0.0
    return float(12 * np.log2(high_hz / low_hz))


def _spread(voiced: np.ndarray) -> float:
    low, high = np.percentile(voiced, [5, 95])
    return semitones(float(high), float(low))


def analyze_pitch(signal: AudioSignal) -> PitchReport:
    pitch = signal.to_sound().to_pitch(
        time_step=TIME_STEP_S, pitch_floor=PITCH_FLOOR_HZ, pitch_ceiling=PITCH_CEILING_HZ
    )
    times = np.asarray(pitch.xs())
    hz = np.asarray(pitch.selected_array["frequency"])
    voiced = hz[hz > 0]
    if voiced.size == 0:
        return PitchReport(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, tuple(times), tuple(hz))

    report_windows = []
    for start, end in windows(signal.duration_s):
        part = hz[(times >= start) & (times < end) & (hz > 0)]
        if part.size < 2:
            continue
        report_windows.append(
            PitchWindow(
                t_start_s=start,
                t_end_s=end,
                mean_hz=round(float(part.mean()), 1),
                std_hz=round(float(part.std()), 1),
                range_semitones=round(_spread(part), 1),
            )
        )

    return PitchReport(
        mean_hz=round(float(voiced.mean()), 1),
        std_hz=round(float(voiced.std()), 1),
        min_hz=round(float(voiced.min()), 1),
        max_hz=round(float(voiced.max()), 1),
        range_semitones=round(_spread(voiced), 1),
        voiced_fraction=round(voiced.size / hz.size, 3),
        times_s=tuple(float(t) for t in times),
        hz=tuple(float(h) for h in hz),
        windows=tuple(report_windows),
    )


def analyze_intonation(pitch: PitchReport) -> IntonationReport:
    times = np.asarray(pitch.times_s)
    hz = np.asarray(pitch.hz)
    is_voiced = hz > 0
    if is_voiced.sum() < 2:
        return IntonationReport(pitch.range_semitones, 1.0, 0.0)

    flat = judged = 0
    for start in np.arange(0, times[-1] + TIME_STEP_S, STRETCH_S):
        part = hz[(times >= start) & (times < start + STRETCH_S) & is_voiced]
        if part.size < STRETCH_MIN_FRAMES:
            continue
        judged += 1
        flat += _spread(part) < FLAT_STRETCH_SEMITONES

    # Speed of movement between neighbouring voiced frames only, so a jump
    # across a pause is not counted as a slide.
    both = is_voiced[1:] & is_voiced[:-1]
    steps = np.abs(12 * np.log2(hz[1:][both] / hz[:-1][both])) / np.diff(times)[both]

    return IntonationReport(
        pitch_range_semitones=pitch.range_semitones,
        monotone_fraction=round(flat / judged, 3) if judged else 1.0,
        pitch_slope_mean=round(float(steps.mean()), 2) if steps.size else 0.0,
    )
