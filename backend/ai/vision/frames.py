"""Sample frames from a video at a steady rate.

Frames are read one at a time, so a long recording never sits in memory.
A frame is kept when its own timestamp reaches the next sample time, so the
times stay right for any source frame rate (a fixed every-Nth-frame step
drifts at 25 or 29.97 fps).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

DEFAULT_FPS = 2.0
# Used when a file does not report its frame rate.
FALLBACK_VIDEO_FPS = 30.0


@dataclass(frozen=True)
class VideoInfo:
    fps: float
    width: int
    height: int
    frame_count: int

    @property
    def aspect(self) -> float:
        """Width over height; landmark x is scaled by this to match y."""
        return self.width / self.height if self.height else 1.0


@dataclass(frozen=True, eq=False)
class SampledFrame:
    index: int  # position in the source video
    time_s: float
    bgr: np.ndarray


def open_video(path: str | Path) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")
    return capture


def video_info(capture: cv2.VideoCapture) -> VideoInfo:
    fps = capture.get(cv2.CAP_PROP_FPS)
    return VideoInfo(
        fps=fps if fps and fps > 0 else FALLBACK_VIDEO_FPS,
        width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        frame_count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
    )


def probe(path: str | Path) -> VideoInfo:
    capture = open_video(path)
    try:
        return video_info(capture)
    finally:
        capture.release()


def sample_frames(path: str | Path, fps: float = DEFAULT_FPS) -> Iterator[SampledFrame]:
    if fps <= 0:
        raise ValueError("fps must be positive")
    capture = open_video(path)
    try:
        source_fps = video_info(capture).fps
        step = 1 / fps
        next_t = 0.0
        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                return
            t = index / source_fps
            # Half a source frame of tolerance absorbs rounding.
            if t + 0.5 / source_fps >= next_t:
                yield SampledFrame(index, round(t, 3), frame)
                next_t += step
            index += 1
    finally:
        capture.release()
