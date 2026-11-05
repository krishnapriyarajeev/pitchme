"""Vision report: posture, eye contact, expression and gestures as findings.

No LLM call; every finding is a threshold over the per-frame measures.
Q&A mode is looser than presentation mode: a speaker who is thinking looks
away and shifts more.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Literal

from ai.core.types import Finding, Severity, TimestampedNote
from ai.utils.media import MediaStore, local_media

from .analyze import FrameAnalysis, analyze_frames
from .frames import DEFAULT_FPS
from .geometry import MAX_SHOULDER_TILT_DEG
from .landmarks import Detector

PIPELINE = "vision"
VisionMode = Literal["presentation", "qa"]

# Tense must be at least this share of face frames to report.
TENSE_SHARE_THRESHOLD = 0.4
# Hands must be in view in this share of body frames, over at least this
# many frame pairs, before gestures are judged.
MIN_HAND_VISIBLE_SHARE = 0.3
MIN_HAND_PAIRS = 5
# Typical hand speed below this (shoulder widths a second) is static.
STATIC_HAND_SPEED = 0.05
# A hand move larger than this between two samples counts as a gesture.
GESTURE_MIN_MOVE = 0.15


@dataclass(frozen=True)
class VisionThresholds:
    eye_contact_low: float
    # Typical hand speed above this, in shoulder widths a second, is fidgety.
    movement_high: float
    poor_posture_share: float


PRESETS: dict[str, VisionThresholds] = {
    "presentation": VisionThresholds(
        eye_contact_low=0.5, movement_high=1.0, poor_posture_share=0.3
    ),
    # Someone thinking of an answer looks away and moves more.
    "qa": VisionThresholds(eye_contact_low=0.3, movement_high=1.4, poor_posture_share=0.5),
}


@dataclass(frozen=True)
class Stretch:
    start_s: float
    end_s: float

    @property
    def seconds(self) -> float:
        return round(self.end_s - self.start_s, 2)


@dataclass(frozen=True)
class PoseAnalysis:
    good_posture_pct: float
    mean_shoulder_tilt_deg: float
    mean_slouch_ratio: float | None
    # "torso" or "neck"; see geometry.slouch.
    slouch_source: str | None
    poor_posture_frames: int
    tilted_frames: int
    slouched_frames: int
    total_frames: int
    longest_poor: Stretch | None = None


@dataclass(frozen=True)
class EyeContactAnalysis:
    contact_pct: float
    total_frames: int
    longest_away: Stretch | None = None


@dataclass(frozen=True)
class EmotionAnalysis:
    dominant_emotion: str
    emotion_distribution: dict[str, float]


@dataclass(frozen=True)
class MovementAnalysis:
    # static, normal, excessive, or unknown when the hands were rarely seen.
    movement_level: str
    hand_visible_pct: float
    # Median wrist speed in shoulder widths a second.
    hand_speed: float
    gestures_per_min: float


@dataclass(frozen=True)
class VisionReport:
    mode: str
    pose: PoseAnalysis
    eye_contact: EyeContactAnalysis
    emotion: EmotionAnalysis
    movement: MovementAnalysis
    frames: tuple[FrameAnalysis, ...]
    findings: tuple[Finding, ...]


def thresholds_for(mode: str) -> VisionThresholds:
    try:
        return PRESETS[mode]
    except KeyError:
        raise ValueError(
            f"Unknown vision mode {mode!r}. Use one of: {', '.join(PRESETS)}"
        ) from None


def _step(frames: Sequence[FrameAnalysis]) -> float:
    if len(frames) < 2:
        return 1 / DEFAULT_FPS
    return statistics.median(b.time_s - a.time_s for a, b in pairwise(frames))


def longest_stretch(
    frames: Sequence[FrameAnalysis], flagged: Callable[[FrameAnalysis], bool | None]
) -> Stretch | None:
    """The longest run of frames where `flagged` is True. Frames where it is
    None (nothing to judge) neither extend nor break a run."""
    step = _step(frames)
    best: tuple[float, float] | None = None
    start: float | None = None
    last = 0.0
    for frame in frames:
        value = flagged(frame)
        if value is None:
            continue
        if value:
            start = frame.time_s if start is None else start
            last = frame.time_s
        elif start is not None:
            if best is None or last - start > best[1] - best[0]:
                best = (start, last)
            start = None
    if start is not None and (best is None or last - start > best[1] - best[0]):
        best = (start, last)
    return Stretch(best[0], round(best[1] + step, 3)) if best else None


def aggregate_pose(frames: Sequence[FrameAnalysis]) -> PoseAnalysis:
    body = [f for f in frames if f.has_body]
    if not body:
        return PoseAnalysis(0.0, 0.0, None, None, 0, 0, 0, 0)
    tilted = sum(1 for f in body if f.shoulder_tilt_deg > MAX_SHOULDER_TILT_DEG)
    slouched = sum(1 for f in body if f.slouch and f.slouch.is_slouching)
    poor = sum(1 for f in body if not f.good_posture)
    readings = [f.slouch for f in body if f.slouch]
    source = Counter(r.source for r in readings).most_common(1)[0][0] if readings else None
    same_source = [r.ratio for r in readings if r.source == source]
    return PoseAnalysis(
        good_posture_pct=round(1 - poor / len(body), 3),
        mean_shoulder_tilt_deg=round(statistics.fmean(f.shoulder_tilt_deg for f in body), 1),
        mean_slouch_ratio=round(statistics.fmean(same_source), 3) if same_source else None,
        slouch_source=source,
        poor_posture_frames=poor,
        tilted_frames=tilted,
        slouched_frames=slouched,
        total_frames=len(body),
        longest_poor=longest_stretch(
            frames, lambda f: None if f.good_posture is None else not f.good_posture
        ),
    )


def aggregate_eye_contact(frames: Sequence[FrameAnalysis]) -> EyeContactAnalysis:
    seen = [f for f in frames if f.has_face]
    if not seen:
        return EyeContactAnalysis(0.0, 0)
    return EyeContactAnalysis(
        contact_pct=round(sum(1 for f in seen if f.eye_contact) / len(seen), 3),
        total_frames=len(seen),
        longest_away=longest_stretch(
            frames, lambda f: None if f.eye_contact is None else not f.eye_contact
        ),
    )


def aggregate_emotion(frames: Sequence[FrameAnalysis]) -> EmotionAnalysis:
    labels = [f.expression for f in frames if f.expression]
    if not labels:
        return EmotionAnalysis("unknown", {})
    counts = Counter(labels)
    return EmotionAnalysis(
        dominant_emotion=counts.most_common(1)[0][0],
        emotion_distribution={k: round(v / len(labels), 3) for k, v in counts.most_common()},
    )


def aggregate_movement(
    frames: Sequence[FrameAnalysis], thresholds: VisionThresholds
) -> MovementAnalysis:
    """Speed of the more active wrist between neighbouring samples, in
    shoulder widths a second, so distance from the camera does not change
    the result and one resting hand does not halve it."""
    body = [f for f in frames if f.has_body]
    visible = sum(1 for f in body if f.wrists) / len(body) if body else 0.0
    moves: list[float] = []
    speeds: list[float] = []
    for a, b in pairwise(frames):
        dt = b.time_s - a.time_s
        if dt <= 0 or not a.shoulder_width or not b.shoulder_width:
            continue
        scale = (a.shoulder_width + b.shoulder_width) / 2
        sides = a.wrists.keys() & b.wrists.keys()
        if not sides:
            continue
        move = max(math.dist(a.wrists[side], b.wrists[side]) for side in sides) / scale
        moves.append(move)
        speeds.append(move / dt)

    if visible < MIN_HAND_VISIBLE_SHARE or len(speeds) < MIN_HAND_PAIRS:
        return MovementAnalysis("unknown", round(visible, 3), 0.0, 0.0)

    speed = statistics.median(speeds)
    seen_minutes = len(speeds) * _step(frames) / 60
    if speed < STATIC_HAND_SPEED:
        level = "static"
    elif speed > thresholds.movement_high:
        level = "excessive"
    else:
        level = "normal"
    return MovementAnalysis(
        movement_level=level,
        hand_visible_pct=round(visible, 3),
        hand_speed=round(speed, 3),
        gestures_per_min=round(sum(m > GESTURE_MIN_MOVE for m in moves) / seen_minutes, 1),
    )


def _clock(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def _note(stretch: Stretch | None) -> TimestampedNote | None:
    if stretch is None:
        return None
    return TimestampedNote(int(stretch.start_s * 1000), int(stretch.end_s * 1000), "")


def _finding(category: str, severity: Severity, summary: str, **kwargs) -> Finding:
    return Finding(
        pipeline=PIPELINE, category=category, severity=severity, summary=summary, **kwargs
    )


def _posture_finding(pose: PoseAnalysis, t: VisionThresholds) -> Finding | None:
    if pose.total_frames == 0:
        return None
    share = pose.poor_posture_frames / pose.total_frames
    if share <= t.poor_posture_share:
        return None
    cause = "leaning shoulders" if pose.tilted_frames >= pose.slouched_frames else "slouching"
    summary = f"Posture slipped in {share:.0%} of the talk, mostly from {cause}."
    if pose.longest_poor:
        stretch = pose.longest_poor
        summary += f" The longest stretch was {_clock(stretch.start_s)}-{_clock(stretch.end_s)}."
    return _finding(
        "poor_posture",
        Severity.MEDIUM,
        summary,
        note=_note(pose.longest_poor),
        details={
            "good_posture_pct": pose.good_posture_pct,
            "mean_shoulder_tilt_deg": pose.mean_shoulder_tilt_deg,
            "mean_slouch_ratio": pose.mean_slouch_ratio,
            "tilted_frames": pose.tilted_frames,
            "slouched_frames": pose.slouched_frames,
        },
    )


def _eye_contact_finding(eyes: EyeContactAnalysis, t: VisionThresholds) -> Finding | None:
    if eyes.total_frames == 0 or eyes.contact_pct >= t.eye_contact_low:
        return None
    summary = f"You looked at the camera {eyes.contact_pct:.0%} of the time."
    if eyes.longest_away:
        away = eyes.longest_away
        summary += (
            f" The longest look away was {away.seconds:.0f} s, at "
            f"{_clock(away.start_s)}-{_clock(away.end_s)}."
        )
    return _finding(
        "low_eye_contact",
        Severity.MEDIUM,
        summary,
        note=_note(eyes.longest_away),
        details={
            "contact_pct": eyes.contact_pct,
            "longest_away_s": eyes.longest_away.seconds if eyes.longest_away else 0.0,
        },
    )


def _movement_finding(movement: MovementAnalysis) -> Finding | None:
    details = {
        "hand_speed": movement.hand_speed,
        "gestures_per_min": movement.gestures_per_min,
        "hand_visible_pct": movement.hand_visible_pct,
    }
    if movement.movement_level == "static":
        return _finding(
            "weak_gesture",
            Severity.LOW,
            "Your hands barely moved. A few gestures help land key points.",
            details=details,
        )
    if movement.movement_level == "excessive":
        return _finding(
            "excessive_movement",
            Severity.LOW,
            "Your hands moved a lot, which can pull attention from what you say.",
            details=details,
        )
    if movement.movement_level == "unknown":
        return _finding(
            "hands_out_of_view",
            Severity.INFO,
            f"Your hands were in view {movement.hand_visible_pct:.0%} of the time, so "
            "gestures were not judged. Frame from the waist up to include them.",
            details=details,
        )
    return None


def _emotion_finding(emotion: EmotionAnalysis) -> Finding | None:
    tense = emotion.emotion_distribution.get("tense", 0.0)
    if tense < TENSE_SHARE_THRESHOLD:
        return None
    return _finding(
        "tense_expression",
        Severity.LOW,
        f"Your face looked tense {tense:.0%} of the time.",
        details={"emotion_distribution": emotion.emotion_distribution},
    )


def build_report(
    frames: tuple[FrameAnalysis, ...], mode: VisionMode = "presentation"
) -> VisionReport:
    t = thresholds_for(mode)
    pose = aggregate_pose(frames)
    eyes = aggregate_eye_contact(frames)
    emotion = aggregate_emotion(frames)
    movement = aggregate_movement(frames, t)

    if pose.total_frames == 0 and eyes.total_frames == 0:
        findings = [
            _finding(
                "no_person",
                Severity.INFO,
                "No person was found in the video, so body language was not measured.",
            )
        ]
    else:
        candidates = (
            _posture_finding(pose, t),
            _eye_contact_finding(eyes, t),
            _movement_finding(movement),
            _emotion_finding(emotion),
        )
        findings = [f for f in candidates if f]
    findings.sort(key=lambda f: (-f.severity.rank, f.note.t_start_ms if f.note else -1))

    return VisionReport(mode, pose, eyes, emotion, movement, frames, tuple(findings))


def score_vision(
    video: str | Path,
    store: MediaStore | None = None,
    *,
    fps: float = DEFAULT_FPS,
    mode: VisionMode = "presentation",
    detector: Detector | None = None,
) -> VisionReport:
    """Analyse a recording given as a local path or a storage key."""
    thresholds_for(mode)  # fail before any download
    with local_media(video, store) as path:
        frames = analyze_frames(path, fps, detector)
    return build_report(frames, mode)
