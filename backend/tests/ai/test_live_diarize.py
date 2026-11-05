"""Real pyannote diarization and voice matching. Needs the diarize extra,
HF_TOKEN with the model licences accepted, and LIVE_AUDIO_SAMPLE: at least
45 s of one person speaking. Runs with make test-live.

There is rarely a two-person recording at hand, so one is built: the
speaker, then the same speaker pitch-shifted down (a different-sounding
voice), then the speaker again.
"""

import os
import shutil
import subprocess

import pytest

from ai.config import AISettings

pytestmark = pytest.mark.live

pytest.importorskip("pyannote.audio", reason="needs the diarize extra")


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    sample = os.environ.get("LIVE_AUDIO_SAMPLE")
    if not sample:
        pytest.skip("LIVE_AUDIO_SAMPLE is not set")
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")
    folder = tmp_path_factory.mktemp("diarize")
    a, b, c, ref = (folder / f"{n}.wav" for n in ("a", "b", "c", "ref"))
    rate = ["-ar", "16000", "-ac", "1"]
    # A quarter lower in pitch at the same speed sounds like another person.
    lower = "asetrate=16000*0.75,aresample=16000,atempo=1.333"
    _ffmpeg("-ss", "0", "-t", "10", "-i", sample, *rate, str(a))
    _ffmpeg("-ss", "10", "-t", "10", "-i", sample, "-af", lower, *rate, str(b))
    _ffmpeg("-ss", "20", "-t", "10", "-i", sample, *rate, str(c))
    _ffmpeg("-ss", "30", "-t", "12", "-i", sample, *rate, str(ref))
    mixed = folder / "mixed.wav"
    inputs = [arg for clip in (a, b, c) for arg in ("-i", str(clip))]
    _ffmpeg(*inputs, "-filter_complex", "concat=n=3:v=0:a=1", str(mixed))
    return mixed, ref


def _token() -> str:
    token = AISettings().hf_token.get_secret_value()
    if not token:
        pytest.skip("HF_TOKEN is not set")
    return token


def test_two_voices_are_found_and_the_user_is_identified(clips):
    from ai.diarize.base import speaking_time
    from ai.diarize.identify import identify_speaker
    from ai.providers.pyannote.diarizer import PyannoteDiarizer
    from ai.providers.pyannote.embedding import PyannoteEmbedder

    mixed, reference = clips
    token = _token()
    segments = PyannoteDiarizer(token).diarize(mixed)
    totals = speaking_time(segments)
    assert len(totals) == 2

    # The shifted voice talks from 10 s to 20 s; the user is the other label.
    shifted = max(
        totals,
        key=lambda s: sum(
            max(0, min(seg.end_ms, 20_000) - max(seg.start_ms, 10_000))
            for seg in segments
            if seg.speaker == s
        ),
    )
    result = identify_speaker(PyannoteEmbedder(token), mixed, segments, reference)
    assert result.speaker != shifted
    assert result.confident
