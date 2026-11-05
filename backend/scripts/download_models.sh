#!/usr/bin/env bash
# Download the MediaPipe models the vision pipeline needs (about 10 MB).
# They are not committed. Run once from backend/:
#
#   ./scripts/download_models.sh [target_dir]
#
# target_dir defaults to ai/models, which is where the pipeline looks unless
# VISION_MODELS_DIR is set.

set -euo pipefail

cd "$(dirname "$0")/.."
TARGET="${1:-ai/models}"
BASE="https://storage.googleapis.com/mediapipe-models"
mkdir -p "$TARGET"

fetch() {
  local name="$1" url="$2"
  if [[ -s "$TARGET/$name" ]]; then
    echo "$name already present"
    return
  fi
  echo "Downloading $name"
  curl -fsSL -o "$TARGET/$name.part" "$url"
  mv "$TARGET/$name.part" "$TARGET/$name"
}

fetch pose_landmarker.task "$BASE/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
fetch face_landmarker.task "$BASE/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
echo "Models are in $TARGET"
