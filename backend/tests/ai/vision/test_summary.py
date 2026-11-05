from ai.vision.report import (
    EmotionAnalysis,
    EyeContactAnalysis,
    MovementAnalysis,
    PoseAnalysis,
    Stretch,
)
from ai.vision.summary import (
    summarize_emotion,
    summarize_eye_contact,
    summarize_movement,
    summarize_pose,
)


def _pose(good_pct, frames=10):
    return PoseAnalysis(good_pct, 4.2, 0.55, "neck", 0, 0, 0, frames)


def test_pose_summary():
    assert "was strong throughout" in summarize_pose(_pose(0.9))
    assert "4.2 degrees" in summarize_pose(_pose(0.9))
    assert "was mostly fine" in summarize_pose(_pose(0.75))
    assert "needs work" in summarize_pose(_pose(0.6))
    assert "was mostly fine" in summarize_pose(_pose(0.6), "qa")
    assert "not measured" in summarize_pose(_pose(0, frames=0))


def test_eye_contact_summary():
    away = Stretch(10.0, 14.5)
    assert summarize_eye_contact(EyeContactAnalysis(0.8, 10)).startswith("Eye contact was strong")
    fair = summarize_eye_contact(EyeContactAnalysis(0.6, 10, away))
    assert fair.startswith("Eye contact was fair")
    assert "longest look away was 4 s" in fair
    assert "too little" in summarize_eye_contact(EyeContactAnalysis(0.4, 10))
    assert "fair" in summarize_eye_contact(EyeContactAnalysis(0.4, 10), "qa")
    short = summarize_eye_contact(EyeContactAnalysis(0.9, 10, Stretch(1.0, 2.0)))
    assert "longest" not in short
    assert "not measured" in summarize_eye_contact(EyeContactAnalysis(0.0, 0))


def test_emotion_summary():
    emotion = EmotionAnalysis("happy", {"happy": 0.6, "neutral": 0.4})
    assert summarize_emotion(emotion) == "Your expression was mostly happy (60% of the time)."
    assert "not measured" in summarize_emotion(EmotionAnalysis("unknown", {}))


def test_movement_summary():
    assert summarize_movement(MovementAnalysis("normal", 0.8, 0.3, 24)).startswith(
        "You gestured a natural amount, about 24"
    )
    assert "almost still" in summarize_movement(MovementAnalysis("static", 0.8, 0.01, 0))
    assert "moved a lot" in summarize_movement(MovementAnalysis("excessive", 0.8, 2.0, 90))
    assert "out of view" in summarize_movement(MovementAnalysis("unknown", 0.1, 0, 0))
