from pathlib import Path

import pytest

from ai.core.types import Severity
from ai.vision.landmarks import Detection
from ai.vision.report import (
    PRESETS,
    Stretch,
    aggregate_movement,
    build_report,
    longest_stretch,
    score_vision,
    thresholds_for,
)

from .conftest import needs_models
from .fakes import FROWN, SMILE, FakeDetector, detection, frames, timeline
from .video import make_video, needs_ffmpeg

PRESENTATION = PRESETS["presentation"]


def _categories(report):
    return [f.category for f in report.findings]


def waving(i: int) -> Detection:
    """Left wrist swinging 0.12 of the width each sample: 0.6 shoulder
    widths, or 1.2 shoulder widths a second at 2 fps."""
    return detection(wrist=(0.3 + 0.12 * (i % 2), 0.8))


def test_good_speaker_has_no_findings():
    report = build_report(timeline(20, lambda i: detection(wrist=(0.3 + 0.02 * (i % 2), 0.8))))
    assert report.findings == ()
    assert report.pose.good_posture_pct == 1.0
    assert report.pose.slouch_source == "neck"
    assert report.eye_contact.contact_pct == 1.0
    assert report.movement.movement_level == "normal"
    assert report.emotion.dominant_emotion == "neutral"


def test_tilted_shoulders_are_poor_posture_with_the_longest_stretch():
    def make(i):
        return detection(tilt_dy=0.1 if 4 <= i < 14 else 0.0)

    report = build_report(timeline(20, make))
    finding = next(f for f in report.findings if f.category == "poor_posture")
    assert finding.severity is Severity.MEDIUM
    assert "leaning shoulders" in finding.summary
    assert (finding.note.t_start_ms, finding.note.t_end_ms) == (2_000, 7_000)
    assert report.pose.tilted_frames == 10
    assert report.pose.longest_poor == Stretch(2.0, 7.0)


def test_slouch_is_named_as_the_cause():
    report = build_report(frames(10, nose_y=0.48))
    finding = next(f for f in report.findings if f.category == "poor_posture")
    assert "slouching" in finding.summary


def test_looking_away_reports_the_longest_look():
    report = build_report(timeline(20, lambda i: detection(looking=i < 6)))
    finding = next(f for f in report.findings if f.category == "low_eye_contact")
    assert report.eye_contact.contact_pct == 0.3
    assert finding.details["longest_away_s"] == 7.0
    assert "0:03-0:10" in finding.summary


def test_qa_mode_allows_more_looking_away_and_slumping():
    def make(i):
        return detection(looking=i % 5 < 2, tilt_dy=0.1 if i % 5 < 2 else 0.0)

    presentation = build_report(timeline(20, make), "presentation")
    qa = build_report(timeline(20, make), "qa")
    assert {"low_eye_contact", "poor_posture"} <= set(_categories(presentation))
    assert "low_eye_contact" not in _categories(qa)
    assert "poor_posture" not in _categories(qa)
    assert qa.mode == "qa"


def test_still_hands_are_weak_gestures():
    report = build_report(frames(20))
    assert report.movement.movement_level == "static"
    assert "weak_gesture" in _categories(report)


def test_waving_hands_are_excessive_in_presentation_but_not_qa():
    moving = timeline(20, waving)
    assert aggregate_movement(moving, PRESENTATION).movement_level == "excessive"
    assert aggregate_movement(moving, PRESETS["qa"]).movement_level == "normal"
    result = aggregate_movement(moving, PRESENTATION)
    assert result.hand_speed == pytest.approx(1.2)
    # One long wave is one gesture: 1 in 9.5 s of hand time.
    assert result.gestures_per_min == 6.3


def test_gestures_count_each_burst_of_movement_once():
    def bursts(i):  # out, further out and back in one go, then still
        return detection(wrist=(0.3 + {1: 0.12, 2: 0.24}.get(i % 5, 0.0), 0.8))

    result = aggregate_movement(timeline(21, bursts), PRESENTATION)
    # Bursts start at samples 1, 6, 11 and 16: 4 gestures in 10 s.
    assert result.gestures_per_min == 24.0


def test_hands_out_of_view_are_not_judged():
    def make(i):
        found = detection()
        hidden = {k: v for k, v in found.pose.items() if "wrist" not in k}
        return Detection(hidden, found.face, found.blendshapes)

    report = build_report(timeline(20, make))
    assert report.movement.movement_level == "unknown"
    finding = next(f for f in report.findings if f.category == "hands_out_of_view")
    assert finding.severity is Severity.INFO


def test_movement_is_measured_in_shoulder_widths():
    near = timeline(20, waving)

    def far(i):  # the same wave, filmed from twice as far away
        found = waving(i)
        half = {
            k: type(p)(0.5 + (p.x - 0.5) / 2, 0.5 + (p.y - 0.5) / 2, p.z, p.visibility)
            for k, p in found.pose.items()
        }
        return Detection(half, found.face, found.blendshapes)

    a = aggregate_movement(near, PRESENTATION).hand_speed
    b = aggregate_movement(timeline(20, far), PRESENTATION).hand_speed
    assert a == pytest.approx(b)


def test_tense_face():
    report = build_report(frames(10, blendshapes=FROWN))
    assert "tense_expression" in _categories(report)
    assert report.emotion.emotion_distribution == {"tense": 1.0}
    happy = build_report(frames(10, blendshapes=SMILE))
    assert happy.emotion.dominant_emotion == "happy"


def test_no_person():
    report = build_report(frames(6, body=False, has_face=False))
    assert _categories(report) == ["no_person"]
    assert report.emotion.dominant_emotion == "unknown"


def test_findings_are_most_severe_first():
    report = build_report(frames(10, looking=False, blendshapes=FROWN, tilt_dy=0.1))
    ranks = [f.severity.rank for f in report.findings]
    assert ranks == sorted(ranks, reverse=True)
    assert all(f.pipeline == "vision" for f in report.findings)


def test_longest_stretch_skips_frames_with_nothing_to_judge():
    run = timeline(6, lambda i: detection(has_face=i != 2, looking=False))
    assert longest_stretch(run, lambda f: f.eye_contact is False or None) == Stretch(0.0, 3.0)
    assert longest_stretch(run[:1], lambda f: True) == Stretch(0.0, 0.5)
    assert longest_stretch(run, lambda f: False) is None


def test_unknown_mode():
    with pytest.raises(ValueError, match="Unknown vision mode 'debate'"):
        thresholds_for("debate")
    with pytest.raises(ValueError):
        score_vision("never-downloaded.mp4", mode="debate")


@needs_ffmpeg
def test_score_vision_from_a_path_and_from_storage(tmp_path):
    video = make_video(tmp_path / "talk.mp4", seconds=2)
    report = score_vision(video, detector=FakeDetector())
    assert len(report.frames) == 4

    class Store:
        def get_file(self, key: str, dest: str | Path) -> Path:
            make_video(Path(dest), seconds=1)
            return Path(dest)

    stored = score_vision("users/1/talk.mp4", Store(), mode="qa", detector=FakeDetector())
    assert stored.mode == "qa"
    assert len(stored.frames) == 2


@needs_ffmpeg
@needs_models
def test_real_models_find_no_person_in_a_test_pattern(tmp_path):
    report = score_vision(make_video(tmp_path / "pattern.mp4", seconds=2, size="320x240"))
    assert _categories(report) == ["no_person"]
