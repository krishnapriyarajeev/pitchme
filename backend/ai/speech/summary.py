"""One-paragraph summaries for the debrief, one per speech measure.

Articulation has no LLM call, so its summary is a template. The fluency
summary adds the pace to the model's own sentence on fillers.
"""

from __future__ import annotations

from .articulation import ArticulationReport
from .fluency import FluencyReport
from .report import CLARITY_SCORE_THRESHOLD, COMFORTABLE_WPM_RANGE


def summarize_fluency(fluency: FluencyReport) -> str:
    if not fluency.wpm_windows:
        return fluency.filler_summary
    low, high = COMFORTABLE_WPM_RANGE
    if fluency.wpm_mean > high:
        pace = "faster than is easy to follow"
    elif fluency.wpm_mean < low:
        pace = "slower than a comfortable pace"
    else:
        pace = "a comfortable pace"
    hesitations = len(fluency.hesitation_pauses)
    text = f"You averaged {fluency.wpm_mean:.0f} words a minute, {pace}."
    if hesitations:
        text += f" You hesitated mid-sentence {hesitations} time{'s' if hesitations > 1 else ''}."
    return f"{text} {fluency.filler_summary}".strip()


def summarize_articulation(articulation: ArticulationReport) -> str:
    if articulation.words_checked == 0:
        return "No confidence scores were available to check articulation."
    unclear = articulation.unclear_words
    if articulation.clarity_score < CLARITY_SCORE_THRESHOLD:
        verdict = "several words were hard to make out"
    elif unclear == 0:
        verdict = "every word was clear"
    else:
        verdict = "articulation was clear overall"
    return (
        f"{unclear} of {articulation.words_checked} words were unclear "
        f"(clarity {articulation.clarity_score:.2f}), so {verdict}."
    )
