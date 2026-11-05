"""Annotated copy of the recording with feedback drawn on every frame.

Overlays: the pose skeleton (green for good posture, red when it slips), a
posture badge, an eye contact light, the expression, the gesture level, a
voice panel when voice data is given, and a bar with the running scores.

OpenCV writes the frames; ffmpeg then encodes them as H.264 with the
original sound, so phones and browsers can play the result.
"""

from __future__ import annotations

import bisect
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from .analyze import FrameAnalysis
from .frames import open_video, video_info

if TYPE_CHECKING:
    from ai.voice import VoiceReport

# Colours are BGR.
GREEN = (80, 200, 80)
RED = (60, 60, 230)
AMBER = (40, 190, 240)
GREY = (170, 170, 170)
WHITE = (255, 255, 255)
CYAN = (230, 200, 90)
PANEL = (30, 30, 30)
FONT = cv2.FONT_HERSHEY_SIMPLEX

BODY_LINES = (
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
)
HAND_LINES = tuple(
    (f"{side}_wrist", f"{side}_{finger}")
    for side in ("left", "right")
    for finger in ("index", "pinky", "thumb")
)
VISIBLE = 0.5

EXPRESSION_COLOURS = {"happy": GREEN, "neutral": AMBER, "surprised": CYAN, "tense": RED}
GESTURE_LABELS = {
    "static": ("Few gestures", AMBER),
    "normal": ("Good gestures", GREEN),
    "excessive": ("Too much motion", RED),
    "unknown": ("Hands not in view", GREY),
}


class AnnotationError(RuntimeError):
    """ffmpeg is missing or could not encode the annotated video."""


@dataclass(frozen=True)
class VoiceWindow:
    t_start_s: float
    t_end_s: float
    pitch_hz: float | None = None
    loudness_db: float | None = None
    rate_sps: float | None = None
    jitter: float | None = None


@dataclass(frozen=True)
class VoiceTimeline:
    windows: tuple[VoiceWindow, ...]
    pitch_hz: float
    loudness_db: float
    rate_range: tuple[float, float]
    jitter_high: float

    def at(self, time_s: float) -> VoiceWindow | None:
        """The latest window that covers `time_s`."""
        found = None
        for window in self.windows:
            if window.t_start_s <= time_s < window.t_end_s:
                found = window
        return found


def voice_timeline(report: VoiceReport) -> VoiceTimeline:
    """Line up the voice report's windows for the overlay."""
    from ai.voice.report import thresholds_for

    merged: dict[tuple[float, float], dict] = {}

    def put(windows, field, value):
        for w in windows:
            merged.setdefault((w.t_start_s, w.t_end_s), {})[field] = value(w)

    put(report.pitch.windows, "pitch_hz", lambda w: w.mean_hz)
    put(report.loudness.windows, "loudness_db", lambda w: w.mean_db)
    put(report.speaking_rate.windows, "rate_sps", lambda w: w.syllables_per_s)
    put(report.nervousness.windows, "jitter", lambda w: w.jitter_local)
    t = thresholds_for(report.mode)
    return VoiceTimeline(
        windows=tuple(VoiceWindow(s, e, **values) for (s, e), values in sorted(merged.items())),
        pitch_hz=report.pitch.mean_hz,
        loudness_db=report.loudness.mean_db,
        rate_range=t.rate_range,
        jitter_high=t.jitter_high,
    )


class _Painter:
    """Draws on one frame, with sizes scaled to the video height."""

    def __init__(self, frame: np.ndarray) -> None:
        self.frame = frame
        self.h, self.w = frame.shape[:2]
        self.s = max(0.6, self.h / 480)

    def px(self, value: float) -> int:
        return round(value * self.s)

    def box(self, x: int, y: int, w: int, h: int, alpha: float = 0.7) -> None:
        x2, y2 = min(self.w, x + w), min(self.h, y + h)
        if x2 <= x or y2 <= y:
            return
        region = self.frame[y:y2, x:x2]
        self.frame[y:y2, x:x2] = cv2.addWeighted(
            region, 1 - alpha, np.full_like(region, PANEL), alpha, 0
        )

    def text(self, text: str, x: int, y: int, colour, size: float = 0.45, bold: int = 1) -> None:
        cv2.putText(
            self.frame,
            text,
            (x, y),
            FONT,
            size * self.s,
            colour,
            max(1, self.px(bold)),
            cv2.LINE_AA,
        )


def _point(painter: _Painter, p) -> tuple[int, int]:
    return int(p.x * painter.w), int(p.y * painter.h)


def draw_skeleton(painter: _Painter, analysis: FrameAnalysis) -> None:
    pose = analysis.detection.pose
    if not pose:
        return
    good = analysis.good_posture
    colour = GREY if good is None else GREEN if good else RED

    def seen(name: str) -> bool:
        return name in pose and pose[name].visibility >= VISIBLE

    for lines, line_colour in ((BODY_LINES, colour), (HAND_LINES, CYAN)):
        for a, b in lines:
            if seen(a) and seen(b):
                cv2.line(
                    painter.frame,
                    _point(painter, pose[a]),
                    _point(painter, pose[b]),
                    line_colour,
                    painter.px(2),
                    cv2.LINE_AA,
                )
    for name, point in pose.items():
        if name != "nose" and seen(name):
            cv2.circle(painter.frame, _point(painter, point), painter.px(3), WHITE, -1, cv2.LINE_AA)


def draw_badges(painter: _Painter, analysis: FrameAnalysis, movement_level: str) -> None:
    p = painter
    pad = p.px(10)

    good = analysis.good_posture
    p.box(pad, pad, p.px(170), p.px(48))
    if good is None:
        p.text("No body in view", pad + p.px(10), pad + p.px(28), GREY)
    else:
        p.text(
            "Good posture" if good else "Fix posture",
            pad + p.px(10),
            pad + p.px(22),
            GREEN if good else RED,
            0.55,
            2,
        )
        p.text(
            f"Tilt {analysis.shoulder_tilt_deg:.1f} deg",
            pad + p.px(10),
            pad + p.px(40),
            WHITE,
            0.38,
        )

    expression = analysis.expression or "no face"
    p.box(pad, pad + p.px(54), p.px(170), p.px(26))
    p.text(
        expression.capitalize(),
        pad + p.px(10),
        pad + p.px(72),
        EXPRESSION_COLOURS.get(expression, GREY),
    )

    label, colour = GESTURE_LABELS.get(movement_level, (movement_level, WHITE))
    p.box(pad, pad + p.px(86), p.px(170), p.px(26))
    p.text(label, pad + p.px(10), pad + p.px(104), colour, 0.42)

    contact = analysis.eye_contact
    x = p.w - p.px(180)
    p.box(x, pad, p.px(170), p.px(30))
    light = GREY if contact is None else GREEN if contact else RED
    cv2.circle(p.frame, (x + p.px(16), pad + p.px(15)), p.px(7), light, -1, cv2.LINE_AA)
    text = "No face" if contact is None else "Eye contact" if contact else "Look at camera"
    p.text(text, x + p.px(30), pad + p.px(20), WHITE, 0.42)


def draw_voice_panel(painter: _Painter, window: VoiceWindow, voice: VoiceTimeline) -> None:
    p = painter
    x, y = p.w - p.px(180), p.px(48)
    p.box(x, y, p.px(170), p.px(92), 0.75)
    rows = []
    if window.pitch_hz is not None:
        steady = abs(window.pitch_hz - voice.pitch_hz) < voice.pitch_hz * 0.3
        rows.append((f"Pitch {window.pitch_hz:.0f} Hz", GREEN if steady else AMBER))
    if window.loudness_db is not None:
        ok = window.loudness_db > voice.loudness_db - 6
        rows.append((f"Volume {window.loudness_db:.1f} dB", GREEN if ok else AMBER))
    if window.rate_sps is not None:
        low, high = voice.rate_range
        ok = low <= window.rate_sps <= high
        rows.append((f"Rate {window.rate_sps:.1f} syl/s", GREEN if ok else AMBER))
    if window.jitter is not None:
        calm = window.jitter <= voice.jitter_high
        rows.append(("Voice relaxed" if calm else "Voice tense", GREEN if calm else AMBER))
    for i, (text, colour) in enumerate(rows):
        p.text(text, x + p.px(10), y + p.px(20 + 20 * i), colour, 0.4)


@dataclass(frozen=True)
class _Running:
    posture: float | None
    eye_contact: float | None
    mood: str


def _running_scores(frames: tuple[FrameAnalysis, ...]) -> list[_Running]:
    """Scores so far at each analysed frame, for the bottom bar."""
    good = body = contact = face = 0
    moods: Counter[str] = Counter()
    out = []
    for f in frames:
        if f.good_posture is not None:
            body += 1
            good += f.good_posture
        if f.eye_contact is not None:
            face += 1
            contact += f.eye_contact
        if f.expression:
            moods[f.expression] += 1
        out.append(
            _Running(
                good / body if body else None,
                contact / face if face else None,
                moods.most_common(1)[0][0] if moods else "-",
            )
        )
    return out


def draw_bar(painter: _Painter, time_s: float, duration_s: float, running: _Running) -> None:
    p = painter
    height = p.px(34)
    top = p.h - height
    p.box(0, top, p.w, height, 0.8)
    progress = min(1.0, time_s / duration_s) if duration_s > 0 else 0.0
    cv2.rectangle(
        p.frame,
        (p.px(10), top + p.px(5)),
        (p.px(10) + int(progress * (p.w - p.px(20))), top + p.px(9)),
        CYAN,
        -1,
    )

    def pct(value: float | None) -> str:
        return "-" if value is None else f"{value:.0%}"

    minutes, seconds = divmod(int(time_s), 60)
    p.text(
        f"{minutes}:{seconds:02d}   Posture {pct(running.posture)}   "
        f"Eye contact {pct(running.eye_contact)}   Mood {running.mood}",
        p.px(10),
        p.h - p.px(9),
        WHITE,
        0.4,
    )


def _encode(raw: Path, source: Path, output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise AnnotationError("ffmpeg is not installed or not on the PATH")
    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(raw), "-i", str(source),
        "-map", "0:v:0", "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", "-shortest",
        str(output),
    ]  # fmt: skip
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise AnnotationError(f"ffmpeg could not encode the video: {result.stderr.strip()[-500:]}")


def render_annotated_video(
    video: str | Path,
    frames: tuple[FrameAnalysis, ...],
    output: str | Path,
    *,
    voice: VoiceTimeline | None = None,
    movement_level: str = "normal",
) -> Path:
    """Write the annotated video to `output` (MP4, H.264, with the source's
    sound if it has any) and return its path."""
    source = Path(video)
    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    times = [f.time_s for f in frames]
    running = _running_scores(frames)

    capture = open_video(source)
    info = video_info(capture)
    duration = info.frame_count / info.fps if info.frame_count else 0.0
    with tempfile.TemporaryDirectory(prefix="pitchme-annotate-") as tmp:
        raw = Path(tmp) / "raw.mp4"
        writer = cv2.VideoWriter(
            str(raw), cv2.VideoWriter_fourcc(*"mp4v"), info.fps, (info.width, info.height)
        )
        try:
            index = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                t = index / info.fps
                at = bisect.bisect_right(times, t + 1e-6) - 1
                if at >= 0:
                    painter = _Painter(frame)
                    draw_skeleton(painter, frames[at])
                    draw_badges(painter, frames[at], movement_level)
                    if voice and (window := voice.at(t)):
                        draw_voice_panel(painter, window, voice)
                    draw_bar(painter, t, duration, running[at])
                writer.write(frame)
                index += 1
        finally:
            capture.release()
            writer.release()
        _encode(raw, source, dest)
    return dest
