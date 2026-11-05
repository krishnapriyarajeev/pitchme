from types import SimpleNamespace

import numpy as np
import pytest

from ai.config import get_ai_settings
from ai.vision import landmarks
from ai.vision.landmarks import (
    FACE_POINTS,
    POSE_POINTS,
    Detection,
    MediaPipeDetector,
    Point,
    VisionModelError,
    _pick,
    models_dir,
    require_models,
)

from .conftest import needs_models


def _lm(x, y, z=None, visibility=None):
    return SimpleNamespace(x=x, y=y, z=z, visibility=visibility)


def test_pick_keeps_named_points_and_their_visibility():
    raw = [_lm(i / 100, 0.5, -0.1, 0.0) for i in range(33)]
    pose = _pick(raw, POSE_POINTS)
    assert set(pose) == set(POSE_POINTS)
    assert pose["left_wrist"] == Point(0.15, 0.5, -0.1, 0.0)


def test_missing_visibility_means_visible():
    assert _pick([_lm(0.1, 0.2)], {"nose": 0}) == {"nose": Point(0.1, 0.2, 0.0, 1.0)}


def test_face_without_iris_points_drops_them():
    face = _pick([_lm(0.5, 0.5)] * 468, FACE_POINTS)
    assert "left_iris" not in face
    assert "nose_tip" in face


def test_detection_defaults_to_nothing_found():
    assert Detection() == Detection(pose={}, face={}, blendshapes={})


def test_models_dir_follows_the_setting(monkeypatch, tmp_path):
    monkeypatch.setenv("VISION_MODELS_DIR", str(tmp_path))
    get_ai_settings.cache_clear()
    try:
        assert models_dir() == tmp_path
    finally:
        get_ai_settings.cache_clear()
    monkeypatch.delenv("VISION_MODELS_DIR")
    monkeypatch.setattr(landmarks, "get_ai_settings", lambda: SimpleNamespace(vision_models_dir=""))
    assert models_dir() == landmarks.DEFAULT_MODELS_DIR


def test_missing_models_name_the_download_script(tmp_path):
    (tmp_path / "pose_landmarker.task").write_bytes(b"x")
    with pytest.raises(VisionModelError, match=r"face_landmarker\.task.*download_models\.sh"):
        require_models(tmp_path)


@needs_models
def test_real_models_find_nothing_in_a_blank_frame():
    detector = MediaPipeDetector()
    try:
        found = detector.detect(np.zeros((240, 320, 3), dtype=np.uint8))
    finally:
        detector.close()
    assert found.pose == {}
    assert found.face == {}
