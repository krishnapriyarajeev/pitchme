"""Vision pipeline: what the video shows about delivery.

Posture, eye contact, expression and gestures from MediaPipe pose and face
landmarks, plus an annotated copy of the video. Needs the `vision` extra and
the models from scripts/download_models.sh.

    from ai.vision import score_vision, render_annotated_video
    report = score_vision("call.mp4", mode="qa")
    render_annotated_video("call.mp4", report.frames, "annotated.mp4",
                           movement_level=report.movement.movement_level)
"""

from .analyze import FrameAnalysis, analyze_frames
from .annotate import AnnotationError, VoiceTimeline, render_annotated_video, voice_timeline
from .frames import DEFAULT_FPS, sample_frames
from .landmarks import Detection, MediaPipeDetector, VisionModelError
from .report import (
    PRESETS,
    EmotionAnalysis,
    EyeContactAnalysis,
    MovementAnalysis,
    PoseAnalysis,
    VisionMode,
    VisionReport,
    build_report,
    score_vision,
)
from .summary import summarize_emotion, summarize_eye_contact, summarize_movement, summarize_pose

__all__ = [
    "DEFAULT_FPS",
    "PRESETS",
    "AnnotationError",
    "Detection",
    "EmotionAnalysis",
    "EyeContactAnalysis",
    "FrameAnalysis",
    "MediaPipeDetector",
    "MovementAnalysis",
    "PoseAnalysis",
    "VisionMode",
    "VisionModelError",
    "VisionReport",
    "VoiceTimeline",
    "analyze_frames",
    "build_report",
    "render_annotated_video",
    "sample_frames",
    "score_vision",
    "summarize_emotion",
    "summarize_eye_contact",
    "summarize_movement",
    "summarize_pose",
    "voice_timeline",
]
