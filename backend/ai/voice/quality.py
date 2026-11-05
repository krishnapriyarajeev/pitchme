"""Voice quality signals that rise with nervousness: jitter, shimmer, HNR.

Jitter is how much the length of each vocal cycle wobbles, shimmer how much
its loudness wobbles, and HNR (harmonics to noise ratio) how clean the voice
is against breath and noise. Microphones and rooms move these numbers too,
so they are also reported per window: a change over the talk means more
than one value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import parselmouth
from parselmouth import praat

from .pitch import PITCH_CEILING_HZ, PITCH_FLOOR_HZ
from .signal import AudioSignal, windows

# Praat's standard arguments for jitter and shimmer: no time range, shortest
# and longest period, largest period factor, largest amplitude factor.
_PERIOD = (0, 0, 0.0001, 0.02, 1.3)
_AMPLITUDE = (*_PERIOD, 1.6)

# Praat marks frames with no voice at -200 dB HNR.
_UNVOICED_HNR = -199.0


@dataclass(frozen=True)
class VoiceQuality:
    jitter_local: float
    shimmer_local: float
    hnr_db: float
    voiced: bool


@dataclass(frozen=True)
class NervousnessWindow:
    t_start_s: float
    t_end_s: float
    jitter_local: float
    shimmer_local: float
    hnr_db: float


@dataclass(frozen=True)
class NervousnessReport:
    jitter_local: float
    shimmer_local: float
    hnr_db: float
    windows: tuple[NervousnessWindow, ...]
    # False when there was no voice to measure; the numbers are then 0.
    voiced: bool = True


def _clean(value: float) -> float:
    return 0.0 if math.isnan(value) or value < 0 else value


def measure_quality(sound: parselmouth.Sound) -> VoiceQuality:
    try:
        points = praat.call(
            sound, "To PointProcess (periodic, cc)", PITCH_FLOOR_HZ, PITCH_CEILING_HZ
        )
        if praat.call(points, "Get number of points") < 3:
            return VoiceQuality(0.0, 0.0, 0.0, voiced=False)
        jitter = praat.call(points, "Get jitter (local)", *_PERIOD)
        shimmer = praat.call([sound, points], "Get shimmer (local)", *_AMPLITUDE)
    except parselmouth.PraatError:
        return VoiceQuality(0.0, 0.0, 0.0, voiced=False)

    harmonicity = sound.to_harmonicity()
    frames = np.asarray(harmonicity.values).ravel()
    frames = frames[frames > _UNVOICED_HNR]
    hnr = float(frames.mean()) if frames.size else 0.0

    return VoiceQuality(
        jitter_local=round(_clean(jitter), 5),
        shimmer_local=round(_clean(shimmer), 5),
        hnr_db=round(hnr, 1),
        voiced=True,
    )


def analyze_nervousness(signal: AudioSignal) -> NervousnessReport:
    sound = signal.to_sound()
    overall = measure_quality(sound)
    if not overall.voiced:
        return NervousnessReport(0.0, 0.0, 0.0, (), voiced=False)

    report_windows = []
    for start, end in windows(signal.duration_s):
        part = measure_quality(sound.extract_part(from_time=start, to_time=end))
        if part.voiced:
            report_windows.append(
                NervousnessWindow(start, end, part.jitter_local, part.shimmer_local, part.hnr_db)
            )

    return NervousnessReport(
        jitter_local=overall.jitter_local,
        shimmer_local=overall.shimmer_local,
        hnr_db=overall.hnr_db,
        windows=tuple(report_windows),
    )
