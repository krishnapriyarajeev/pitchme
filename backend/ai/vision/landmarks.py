"""Body and face landmarks for one frame, and the detector that finds them.

`MediaPipeDetector` runs the Pose Landmarker and the Face Landmarker
(MediaPipe Tasks). Everything after it works on the plain `Detection` it
returns, so tests can pass a fake detector and never load a model.

Coordinates are normalized: x from 0 at the left edge to 1 at the right, y
from 0 at the top to 1 at the bottom.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from ai.config import get_ai_settings

POSE_MODEL = "pose_landmarker.task"
FACE_MODEL = "face_landmarker.task"
DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# MediaPipe pose landmark indices.
POSE_POINTS = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_pinky": 17,
    "right_pinky": 18,
    "left_index": 19,
    "right_index": 20,
    "left_thumb": 21,
    "right_thumb": 22,
    "left_hip": 23,
    "right_hip": 24,
}

# Face landmark indices. Iris centres exist only in the 478 point model.
FACE_POINTS = {
    "nose_tip": 1,
    "left_eye_outer": 33,
    "left_eye_inner": 133,
    "right_eye_inner": 362,
    "right_eye_outer": 263,
    "left_iris": 468,
    "right_iris": 473,
}


class VisionModelError(RuntimeError):
    """A model file is missing, or mediapipe or a library it needs is not installed."""


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0
    # The model's confidence that the point is in view, from 0 to 1.
    visibility: float = 1.0


@dataclass(frozen=True)
class Detection:
    """What the detector saw in one frame. Empty dicts mean nothing found."""

    pose: dict[str, Point] = field(default_factory=dict)
    face: dict[str, Point] = field(default_factory=dict)
    # MediaPipe face blendshape scores (0 to 1), for example mouthSmileLeft.
    blendshapes: dict[str, float] = field(default_factory=dict)


class Detector(Protocol):
    def detect(self, rgb: np.ndarray) -> Detection: ...

    def close(self) -> None: ...


def models_dir() -> Path:
    configured = get_ai_settings().vision_models_dir.strip()
    return Path(configured) if configured else DEFAULT_MODELS_DIR


def require_models(directory: Path | None = None) -> tuple[Path, Path]:
    folder = directory or models_dir()
    paths = (folder / POSE_MODEL, folder / FACE_MODEL)
    missing = [p.name for p in paths if not p.is_file()]
    if missing:
        raise VisionModelError(
            f"Missing {', '.join(missing)} in {folder}. Run ./scripts/download_models.sh"
        )
    return paths


def _point(lm) -> Point:
    z = getattr(lm, "z", None)
    visibility = getattr(lm, "visibility", None)
    return Point(
        float(lm.x),
        float(lm.y),
        0.0 if z is None else float(z),
        1.0 if visibility is None else float(visibility),
    )


def _pick(landmarks, indices: dict[str, int]) -> dict[str, Point]:
    return {name: _point(landmarks[i]) for name, i in indices.items() if i < len(landmarks)}


class MediaPipeDetector:
    """Pose and face landmarks for still images, one person and one face."""

    def __init__(self, directory: Path | None = None) -> None:
        pose_path, face_path = require_models(directory)
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
        except ImportError as exc:  # pragma: no cover - depends on the install
            raise VisionModelError(
                "mediapipe is not installed. Run: uv sync --extra vision"
            ) from exc

        self._mp = mp
        image_mode = vision.RunningMode.IMAGE
        try:
            self._pose = vision.PoseLandmarker.create_from_options(
                vision.PoseLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(pose_path)),
                    running_mode=image_mode,
                    num_poses=1,
                )
            )
        except OSError as exc:
            # mediapipe loads its native library on first use, and that
            # library needs the system EGL and GLES libraries.
            raise VisionModelError(
                f"mediapipe could not load its native library ({exc}). "
                "On Debian or Ubuntu run: apt-get install libegl1 libgles2"
            ) from exc
        self._face = vision.FaceLandmarker.create_from_options(
            vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(face_path)),
                running_mode=image_mode,
                num_faces=1,
                output_face_blendshapes=True,
            )
        )

    def detect(self, rgb: np.ndarray) -> Detection:
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        pose = self._pose.detect(image)
        face = self._face.detect(image)
        blendshapes = {}
        if face.face_blendshapes:
            blendshapes = {c.category_name: float(c.score) for c in face.face_blendshapes[0]}
        return Detection(
            pose=_pick(pose.pose_landmarks[0], POSE_POINTS) if pose.pose_landmarks else {},
            face=_pick(face.face_landmarks[0], FACE_POINTS) if face.face_landmarks else {},
            blendshapes=blendshapes,
        )

    def close(self) -> None:
        self._pose.close()
        self._face.close()
