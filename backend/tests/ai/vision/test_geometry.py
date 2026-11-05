import pytest

from ai.vision import geometry as g
from ai.vision.landmarks import Point

WIDE = 16 / 9


def body(
    *,
    left=(0.4, 0.5),
    right=(0.6, 0.5),
    hips=(0.95, 0.95),
    hip_visibility=0.9,
    nose_y=0.3,
    wrist_visibility=0.9,
):
    """A front-facing body; shoulders are 0.2 of the width apart."""
    return {
        "left_shoulder": Point(*left),
        "right_shoulder": Point(*right),
        "left_hip": Point(0.42, hips[0], visibility=hip_visibility),
        "right_hip": Point(0.58, hips[1], visibility=hip_visibility),
        "nose": Point(0.5, nose_y),
        "left_wrist": Point(0.3, 0.8, visibility=wrist_visibility),
        "right_wrist": Point(0.7, 0.8, visibility=0.1),
    }


def test_level_shoulders_in_a_wide_frame_are_level():
    assert g.shoulder_tilt(body(), WIDE) == 0.0


def test_tilt_uses_aspect_corrected_units():
    # 0.1 of the height over 0.2 of a 16:9 width: atan(0.1 / 0.356) = 15.7 degrees.
    pose = body(left=(0.4, 0.45), right=(0.6, 0.55))
    assert g.shoulder_tilt(pose, WIDE) == pytest.approx(15.7, abs=0.1)
    # Without the correction it would read as 26.6 degrees.
    assert g.shoulder_tilt(pose, 1.0) == pytest.approx(26.6, abs=0.1)


def test_hidden_shoulder_means_no_reading():
    pose = body()
    pose["left_shoulder"] = Point(0.4, 0.5, visibility=0.2)
    assert g.shoulder_tilt(pose, WIDE) is None
    assert g.slouch(pose, WIDE) is None
    assert g.good_posture(None, None) is None


def test_slouch_from_torso_when_hips_are_in_view():
    width = 0.2 * WIDE
    upright = g.slouch(body(), WIDE)
    assert upright == g.Slouch(round(0.45 / width, 3), "torso")
    assert not upright.is_slouching
    hunched = g.slouch(body(hips=(0.75, 0.75)), WIDE)
    assert hunched.is_slouching


def test_slouch_from_neck_when_hips_are_out_of_view():
    upright = g.slouch(body(hip_visibility=0.1), WIDE)
    assert upright.source == "neck"
    assert not upright.is_slouching
    head_down = g.slouch(body(hip_visibility=0.1, nose_y=0.45), WIDE)
    assert head_down.is_slouching


def test_no_hips_and_no_nose():
    pose = body(hip_visibility=0.1)
    del pose["nose"]
    assert g.slouch(pose, WIDE) is None


def test_good_posture():
    assert g.good_posture(3.0, g.Slouch(1.2, "torso"))
    assert g.good_posture(3.0, None)
    assert not g.good_posture(12.0, g.Slouch(1.2, "torso"))
    assert not g.good_posture(3.0, g.Slouch(0.5, "torso"))


def face(iris_shift=0.0, nose_x=0.5):
    """Eyes from 0.40-0.46 and 0.54-0.60; irises centred unless shifted."""
    return {
        "left_eye_outer": Point(0.40, 0.4),
        "left_eye_inner": Point(0.46, 0.4),
        "right_eye_inner": Point(0.54, 0.4),
        "right_eye_outer": Point(0.60, 0.4),
        "left_iris": Point(0.43 + iris_shift, 0.4),
        "right_iris": Point(0.57 + iris_shift, 0.4),
        "nose_tip": Point(nose_x, 0.45),
    }


def test_eye_contact():
    assert g.eye_contact(face()) is True
    assert g.eye_contact(face(iris_shift=0.02)) is False  # looking aside
    assert g.eye_contact(face(nose_x=0.58)) is False  # head turned


def test_eye_contact_without_iris_points_is_unknown():
    no_iris = face()
    del no_iris["left_iris"]
    assert g.eye_contact(no_iris) is None
    no_nose = face()
    del no_nose["nose_tip"]
    assert g.eye_contact(no_nose) is None
    flat = face()
    flat["left_eye_inner"] = Point(0.40, 0.4)
    assert g.eye_contact(flat) is None


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ({"mouthSmileLeft": 0.6, "mouthSmileRight": 0.5}, "happy"),
        ({"browInnerUp": 0.7, "eyeWideLeft": 0.5, "eyeWideRight": 0.4}, "surprised"),
        ({"browDownLeft": 0.5, "browDownRight": 0.4}, "tense"),
        ({"mouthPressLeft": 0.6, "mouthPressRight": 0.5}, "tense"),
        ({"browInnerUp": 0.7}, "neutral"),
        ({"jawOpen": 0.2}, "neutral"),
        ({}, None),
    ],
)
def test_expression(scores, expected):
    assert g.expression(scores) == expected


def test_only_visible_wrists_are_kept():
    found = g.wrists(body(), WIDE)
    assert list(found) == ["left"]
    assert found["left"] == pytest.approx((0.3 * WIDE, 0.8))
