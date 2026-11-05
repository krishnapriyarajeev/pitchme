"""Small test videos made with ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def make_video(
    path: Path,
    seconds: float = 2.0,
    fps: float = 25,
    size: str = "160x120",
    audio: bool = False,
) -> Path:
    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size={size}:rate={fps}",
    ]  # fmt: skip
    if audio:
        command += ["-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}"]
        command += ["-c:a", "aac", "-shortest"]
    command += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(command, check=True, capture_output=True)
    return path


def streams(path: Path) -> dict[str, str]:
    """codec_type -> codec_name for each stream in the file."""
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type,codec_name",
            "-of", "csv=p=0", str(path),
        ],
        check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    pairs = [line.split(",") for line in out.split()]
    return {kind: name for name, kind in pairs}
