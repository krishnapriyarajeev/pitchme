import pytest

from ai.vision.landmarks import DEFAULT_MODELS_DIR, FACE_MODEL, POSE_MODEL

HAVE_MODELS = all((DEFAULT_MODELS_DIR / name).is_file() for name in (POSE_MODEL, FACE_MODEL))

needs_models = pytest.mark.skipif(
    not HAVE_MODELS, reason="MediaPipe models not downloaded (scripts/download_models.sh)"
)
