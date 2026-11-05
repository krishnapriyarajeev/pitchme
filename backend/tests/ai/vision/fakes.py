"""Landmark data for vision tests, without models."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from ai.vision.analyze import FrameAnalysis, measure
from ai.vision.landmarks import Detection, Point

ASPECT = 16 / 9


def pose(
    tilt_dy: float = 0.0,
    nose_y: float = 0.3,
    wrist: tuple[float, float] = (0.3, 0.8),
    hips_visible: bool = False,
) -> dict[str, Point]:
    hip_visibility = 0.9 if hips_visible else 0.1
    return {
        "nose": Point(0.5, nose_y),
        "left_shoulder": Point(0.4, 0.5 - tilt_dy / 2),
        "right_shoulder": Point(0.6, 0.5 + tilt_dy / 2),
        "left_elbow": Point(0.35, 0.65),
        "right_elbow": Point(0.65, 0.65),
        "left_wrist": Point(*wrist),
        "right_wrist": Point(0.7, 0.8),
        "left_hip": Point(0.42, 0.95, visibility=hip_visibility),
        "right_hip": Point(0.58, 0.95, visibility=hip_visibility),
    }


def face(looking: bool = True) -> dict[str, Point]:
    shift = 0.0 if looking else 0.025
    return {
        "nose_tip": Point(0.5, 0.35),
        "left_eye_outer": Point(0.46, 0.3),
        "left_eye_inner": Point(0.49, 0.3),
        "right_eye_inner": Point(0.51, 0.3),
        "right_eye_outer": Point(0.54, 0.3),
        "left_iris": Point(0.475 + shift, 0.3),
        "right_iris": Point(0.525 + shift, 0.3),
    }


SMILE = {"mouthSmileLeft": 0.6, "mouthSmileRight": 0.6}
CALM = {"jawOpen": 0.1}
FROWN = {"browDownLeft": 0.6, "browDownRight": 0.6}


def detection(
    *,
    body: bool = True,
    looking: bool = True,
    has_face: bool = True,
    blendshapes: dict[str, float] | None = None,
    **pose_args,
) -> Detection:
    return Detection(
        pose=pose(**pose_args) if body else {},
        face=face(looking) if has_face else {},
        blendshapes=(blendshapes if blendshapes is not None else CALM) if has_face else {},
    )


def frames(count: int, fps: float = 2.0, **kwargs) -> tuple[FrameAnalysis, ...]:
    """`count` identical frames; kwargs as for detection()."""
    return tuple(measure(detection(**kwargs), i, round(i / fps, 3), ASPECT) for i in range(count))


def timeline(count: int, make: Callable[[int], Detection], fps: float = 2.0):
    """Frames whose detection depends on the frame number."""
    return tuple(measure(make(i), i, round(i / fps, 3), ASPECT) for i in range(count))


class FakeDetector:
    def __init__(self, result: Detection | None = None) -> None:
        self.result = result or detection()
        self.seen: list[tuple[int, ...]] = []
        self.closed = False

    def detect(self, rgb: np.ndarray) -> Detection:
        self.seen.append(rgb.shape)
        return self.result

    def close(self) -> None:
        self.closed = True
