"""Speech pipeline: what the transcript shows about delivery.

Input is a `Transcript`, not audio. Fillers take one LLM call; everything
else is arithmetic over word timings and confidence.

    from ai.speech import score_speech
    report = score_speech(transcript)
"""

from .articulation import ArticulationFlag, ArticulationReport, score_articulation
from .fluency import FluencyReport, score_fluency
from .report import SpeechReport, score_speech
from .summary import summarize_articulation, summarize_fluency

__all__ = [
    "ArticulationFlag",
    "ArticulationReport",
    "FluencyReport",
    "SpeechReport",
    "score_articulation",
    "score_fluency",
    "score_speech",
    "summarize_articulation",
    "summarize_fluency",
]
