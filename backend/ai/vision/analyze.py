"""Run the detector over sampled frames and measure each one."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2

from . import geometry
from .frames import DEFAULT_FPS, probe, sample_frames
from .landmarks import Detection, Detector, MediaPipeDetector


@dataclass(frozen=True)
class FrameAnalysis:
    index: int  # position in the source video
    time_s: float
    detection: Detection
    shoulder_tilt_deg: float | None
    slouch: geometry.Slouch | None
    eye_contact: bool | None
    expression: str | None
    # Visible wrists and the shoulder width, in aspect-corrected units.
    wrists: dict[str, tuple[float, float]] = field(default_factory=dict)
    shoulder_width: float | None = None

    @property
    def has_body(self) -> bool:
        return self.shoulder_tilt_deg is not None

    @property
    def has_face(self) -> bool:
        return self.eye_contact is not None

    @property
    def good_posture(self) -> bool | None:
        return geometry.good_posture(self.shoulder_tilt_deg, self.slouch)


def measure(detection: Detection, index: int, time_s: float, aspect: float) -> FrameAnalysis:
    pose = detection.pose
    return FrameAnalysis(
        index=index,
        time_s=time_s,
        detection=detection,
        shoulder_tilt_deg=geometry.shoulder_tilt(pose, aspect),
        slouch=geometry.slouch(pose, aspect),
        eye_contact=geometry.eye_contact(detection.face),
        expression=geometry.expression(detection.blendshapes),
        wrists=geometry.wrists(pose, aspect),
        shoulder_width=geometry.shoulder_width(pose, aspect),
    )


def analyze_frames(
    video: str | Path, fps: float = DEFAULT_FPS, detector: Detector | None = None
) -> tuple[FrameAnalysis, ...]:
    """Measure every sampled frame. The detector is closed afterwards only
    if this function created it."""
    aspect = probe(video).aspect
    own = detector is None
    detector = detector or MediaPipeDetector()
    try:
        return tuple(
            measure(
                detector.detect(cv2.cvtColor(frame.bgr, cv2.COLOR_BGR2RGB)),
                frame.index,
                frame.time_s,
                aspect,
            )
            for frame in sample_frames(video, fps)
        )
    finally:
        if own:
            detector.close()
