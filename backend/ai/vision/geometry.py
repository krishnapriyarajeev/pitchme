"""Measures for one frame: posture, eye contact, expression and hands.

Landmark x is a share of the frame width and y a share of its height, so x
is multiplied by the aspect ratio (width / height) before any angle or
length is taken. Without that, a level pair of shoulders in a 16:9 video
reads as tilted, and torso length is compared in the wrong units.

A point the pose model marks as out of view (visibility below VISIBLE) is
never used. In a webcam shot the hips are usually out of frame, so slouch
falls back to how far the head sits above the shoulders.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .landmarks import FACE_POINTS, Point

VISIBLE = 0.5

# Shoulders more than this far from level are tilted.
MAX_SHOULDER_TILT_DEG = 10.0
# Torso height under this many shoulder widths is a slouch (hips in view).
MIN_TORSO_RATIO = 0.8
# Nose less than this many shoulder widths above the shoulders is a slouch
# (hips out of view).
MIN_NECK_RATIO = 0.3

# The iris must sit within this distance of the middle of the eye, as a
# share of the eye's width, and the nose within this distance of the middle
# between the outer eye corners, for the speaker to be looking at the camera.
IRIS_TOLERANCE = 0.2
HEAD_TURN_TOLERANCE = 0.2

# Blendshape scores (0 to 1) that decide the expression.
SMILE_MIN = 0.35
BROW_DOWN_MIN = 0.35
MOUTH_PRESS_MIN = 0.4
BROW_UP_MIN = 0.5
EYE_WIDE_MIN = 0.3

EXPRESSIONS = ("happy", "surprised", "tense", "neutral")


@dataclass(frozen=True)
class Slouch:
    ratio: float
    # "torso" when the hips were in view, "neck" when they were not.
    source: str

    @property
    def is_slouching(self) -> bool:
        limit = MIN_TORSO_RATIO if self.source == "torso" else MIN_NECK_RATIO
        return self.ratio < limit


def _xy(point: Point, aspect: float) -> tuple[float, float]:
    return point.x * aspect, point.y


def _visible(pose: dict[str, Point], *names: str) -> bool:
    return all(name in pose and pose[name].visibility >= VISIBLE for name in names)


def shoulder_width(pose: dict[str, Point], aspect: float) -> float | None:
    if not _visible(pose, "left_shoulder", "right_shoulder"):
        return None
    width = math.dist(_xy(pose["left_shoulder"], aspect), _xy(pose["right_shoulder"], aspect))
    return width if width > 1e-6 else None


def shoulder_tilt(pose: dict[str, Point], aspect: float) -> float | None:
    """Degrees from level, whichever way the shoulders lean."""
    if shoulder_width(pose, aspect) is None:
        return None
    lx, ly = _xy(pose["left_shoulder"], aspect)
    rx, ry = _xy(pose["right_shoulder"], aspect)
    return round(math.degrees(math.atan2(abs(ry - ly), abs(rx - lx))), 1)


def slouch(pose: dict[str, Point], aspect: float) -> Slouch | None:
    width = shoulder_width(pose, aspect)
    if width is None:
        return None
    shoulder_y = (pose["left_shoulder"].y + pose["right_shoulder"].y) / 2
    if _visible(pose, "left_hip", "right_hip"):
        hip_y = (pose["left_hip"].y + pose["right_hip"].y) / 2
        return Slouch(round(abs(hip_y - shoulder_y) / width, 3), "torso")
    if _visible(pose, "nose"):
        return Slouch(round((shoulder_y - pose["nose"].y) / width, 3), "neck")
    return None


def good_posture(tilt: float | None, reading: Slouch | None) -> bool | None:
    """None when there was no body to judge."""
    if tilt is None:
        return None
    return tilt <= MAX_SHOULDER_TILT_DEG and not (reading and reading.is_slouching)


def _share_across(point: Point, start: Point, end: Point) -> float | None:
    """Where `point` sits between `start` and `end` along x, from 0 to 1."""
    span = end.x - start.x
    if abs(span) < 1e-6:
        return None
    return (point.x - start.x) / span


def eye_contact(face: dict[str, Point]) -> bool | None:
    """True when both irises are centred and the head faces the camera.
    None when the face or its iris points were not found."""
    if not all(name in face for name in FACE_POINTS):
        return None
    left = _share_across(face["left_iris"], face["left_eye_outer"], face["left_eye_inner"])
    right = _share_across(face["right_iris"], face["right_eye_inner"], face["right_eye_outer"])
    head = _share_across(face["nose_tip"], face["left_eye_outer"], face["right_eye_outer"])
    if left is None or right is None or head is None:
        return None
    return (
        abs(left - 0.5) <= IRIS_TOLERANCE
        and abs(right - 0.5) <= IRIS_TOLERANCE
        and abs(head - 0.5) <= HEAD_TURN_TOLERANCE
    )


def _pair(blendshapes: dict[str, float], name: str) -> float:
    return (blendshapes.get(f"{name}Left", 0.0) + blendshapes.get(f"{name}Right", 0.0)) / 2


def expression(blendshapes: dict[str, float]) -> str | None:
    """happy, surprised, tense or neutral from MediaPipe blendshapes; None
    when there was no face."""
    if not blendshapes:
        return None
    if _pair(blendshapes, "mouthSmile") >= SMILE_MIN:
        return "happy"
    if blendshapes.get("browInnerUp", 0.0) >= BROW_UP_MIN and _pair(blendshapes, "eyeWide") >= (
        EYE_WIDE_MIN
    ):
        return "surprised"
    if (
        _pair(blendshapes, "browDown") >= BROW_DOWN_MIN
        or _pair(blendshapes, "mouthPress") >= MOUTH_PRESS_MIN
    ):
        return "tense"
    return "neutral"


def wrists(pose: dict[str, Point], aspect: float) -> dict[str, tuple[float, float]]:
    """Visible wrists in aspect-corrected coordinates."""
    return {
        side: _xy(pose[f"{side}_wrist"], aspect)
        for side in ("left", "right")
        if _visible(pose, f"{side}_wrist")
    }
