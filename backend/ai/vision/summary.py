"""One-sentence summaries for the debrief, one per vision measure.
Templates only; there is no LLM in the vision pipeline."""

from __future__ import annotations

from .report import (
    PRESETS,
    EmotionAnalysis,
    EyeContactAnalysis,
    MovementAnalysis,
    PoseAnalysis,
)

STRONG_POSTURE_PCT = 0.85
STRONG_EYE_CONTACT_PCT = 0.75


def summarize_pose(pose: PoseAnalysis, mode: str = "presentation") -> str:
    if pose.total_frames == 0:
        return "Your body was not in view, so posture was not measured."
    if 1 - pose.good_posture_pct > PRESETS[mode].poor_posture_share:
        verdict = "needs work"
    elif pose.good_posture_pct >= STRONG_POSTURE_PCT:
        verdict = "was strong throughout"
    else:
        verdict = "was mostly fine"
    return (
        f"Your posture {verdict}: good {pose.good_posture_pct:.0%} of the time, with "
        f"shoulders {pose.mean_shoulder_tilt_deg:.1f} degrees off level on average."
    )


def summarize_eye_contact(eyes: EyeContactAnalysis, mode: str = "presentation") -> str:
    if eyes.total_frames == 0:
        return "Your face was not in view, so eye contact was not measured."
    if eyes.contact_pct < PRESETS[mode].eye_contact_low:
        verdict = "too little"
    elif eyes.contact_pct >= STRONG_EYE_CONTACT_PCT:
        verdict = "strong"
    else:
        verdict = "fair"
    text = f"Eye contact was {verdict}: {eyes.contact_pct:.0%} of the time."
    if eyes.longest_away and eyes.longest_away.seconds >= 2:
        text += f" Your longest look away was {eyes.longest_away.seconds:.0f} s."
    return text


def summarize_emotion(emotion: EmotionAnalysis) -> str:
    if not emotion.emotion_distribution:
        return "Your face was not in view, so expression was not measured."
    share = emotion.emotion_distribution[emotion.dominant_emotion]
    return f"Your expression was mostly {emotion.dominant_emotion} ({share:.0%} of the time)."


def summarize_movement(movement: MovementAnalysis) -> str:
    if movement.movement_level == "unknown":
        return "Your hands were mostly out of view, so gestures were not measured."
    described = {
        "static": "Your hands stayed almost still",
        "normal": "You gestured a natural amount",
        "excessive": "Your hands moved a lot",
    }[movement.movement_level]
    return f"{described}, about {movement.gestures_per_min:.0f} gestures a minute."
