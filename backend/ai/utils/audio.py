"""Audio conversion with ffmpeg, which must be on the PATH.

Every analysis step reads 16 kHz mono 16-bit PCM WAV, so recordings (mp4)
and voice samples (m4a, webm, mp3) are converted with `extract_audio` first.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SAMPLE_RATE = 16_000
CHANNELS = 1


class AudioExtractionError(RuntimeError):
    """ffmpeg is missing or could not convert the file."""


def extract_audio(
    source: str | Path,
    dest: str | Path | None = None,
    *,
    sample_rate: int = SAMPLE_RATE,
    channels: int = CHANNELS,
    timeout_s: float = 600,
) -> Path:
    """Write the audio track of `source` as PCM WAV and return its path.

    `dest` defaults to `source` with a .wav suffix. When `source` is already
    a .wav and `dest` is not given, the output is `<name>.16k.wav` so the
    input is never overwritten.
    """
    src = Path(source)
    if not src.is_file():
        raise FileNotFoundError(f"Media file not found: {src}")
    if dest is None:
        dest = src.with_suffix(".16k.wav" if src.suffix.lower() == ".wav" else ".wav")
    out = Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise AudioExtractionError("ffmpeg is not installed or not on the PATH")

    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(out),
    ]  # fmt: skip
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        raise AudioExtractionError(
            f"ffmpeg took longer than {timeout_s:.0f}s on {src.name}"
        ) from exc
    if result.returncode != 0:
        raise AudioExtractionError(
            f"ffmpeg failed on {src.name} (exit {result.returncode}): {result.stderr.strip()[-500:]}"
        )
    if not out.is_file() or out.stat().st_size == 0:
        raise AudioExtractionError(
            f"ffmpeg wrote no audio for {src.name}; does it have a sound track?"
        )
    return out
