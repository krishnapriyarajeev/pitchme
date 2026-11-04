"""Voice pipeline: what the waveform shows about delivery.

Pitch, intonation, loudness, nervousness (jitter, shimmer, HNR) and syllable
rate, read from the audio itself with Praat. It pairs with ai.speech, which
reads the transcript. Needs the `voice` extra.

    from ai.voice import score_voice
    report = score_voice("call.wav", mode="qa")
"""

from .loudness import LoudnessReport, LoudnessWindow, analyze_loudness
from .pitch import IntonationReport, PitchReport, PitchWindow, analyze_intonation, analyze_pitch
from .quality import NervousnessReport, NervousnessWindow, analyze_nervousness
from .rate import RateWindow, SpeakingRateReport, analyze_rate
from .report import PRESETS, AnalysisMode, VoiceReport, analyze_voice, score_voice
from .signal import AudioSignal, load_audio
from .summary import (
    summarize_loudness,
    summarize_nervousness,
    summarize_pitch,
    summarize_speaking_rate,
    voice_narrative,
)

__all__ = [
    "PRESETS",
    "AnalysisMode",
    "AudioSignal",
    "IntonationReport",
    "LoudnessReport",
    "LoudnessWindow",
    "NervousnessReport",
    "NervousnessWindow",
    "PitchReport",
    "PitchWindow",
    "RateWindow",
    "SpeakingRateReport",
    "VoiceReport",
    "analyze_intonation",
    "analyze_loudness",
    "analyze_nervousness",
    "analyze_pitch",
    "analyze_rate",
    "analyze_voice",
    "load_audio",
    "score_voice",
    "summarize_loudness",
    "summarize_nervousness",
    "summarize_pitch",
    "summarize_speaking_rate",
    "voice_narrative",
]
