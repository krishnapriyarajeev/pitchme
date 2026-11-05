import pytest

from ai.vision.frames import probe, sample_frames

from .video import make_video, needs_ffmpeg

pytestmark = needs_ffmpeg


@pytest.mark.parametrize("source_fps", [25, 30, 29.97])
def test_samples_two_frames_a_second_at_any_source_rate(tmp_path, source_fps):
    video = make_video(tmp_path / "v.mp4", seconds=3, fps=source_fps)
    frames = list(sample_frames(video, fps=2.0))
    assert [round(f.time_s * 2) / 2 for f in frames] == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    assert all(abs(f.time_s - i * 0.5) < 1 / source_fps for i, f in enumerate(frames))
    assert frames[0].bgr.shape == (120, 160, 3)


def test_index_points_into_the_source(tmp_path):
    video = make_video(tmp_path / "v.mp4", seconds=2, fps=30)
    assert [f.index for f in sample_frames(video, fps=1.0)] == [0, 30]


def test_probe(tmp_path):
    info = probe(make_video(tmp_path / "v.mp4", seconds=1, fps=25, size="320x180"))
    assert (info.width, info.height, info.fps) == (320, 180, 25)
    assert info.aspect == pytest.approx(16 / 9)
    assert info.frame_count == 25


def test_bad_inputs(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(sample_frames(tmp_path / "missing.mp4"))
    with pytest.raises(ValueError):
        list(sample_frames(tmp_path / "missing.mp4", fps=0))
