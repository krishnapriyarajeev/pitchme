from ai.vision import analyze as analyze_module
from ai.vision.analyze import analyze_frames, measure
from ai.vision.landmarks import Detection

from .fakes import ASPECT, FakeDetector, detection
from .video import make_video, needs_ffmpeg


def test_measure_a_good_frame():
    frame = measure(detection(), 5, 2.5, ASPECT)
    assert (frame.index, frame.time_s) == (5, 2.5)
    assert frame.has_body
    assert frame.has_face
    assert frame.shoulder_tilt_deg == 0.0
    assert frame.slouch.source == "neck"
    assert frame.good_posture is True
    assert frame.eye_contact is True
    assert frame.expression == "neutral"
    assert set(frame.wrists) == {"left", "right"}
    assert frame.shoulder_width > 0


def test_measure_an_empty_frame():
    frame = measure(Detection(), 0, 0.0, ASPECT)
    assert not frame.has_body
    assert not frame.has_face
    assert frame.good_posture is None
    assert frame.expression is None
    assert frame.wrists == {}


@needs_ffmpeg
def test_runs_the_detector_on_each_sample_in_rgb(tmp_path):
    video = make_video(tmp_path / "v.mp4", seconds=2, fps=25, size="160x90")
    fake = FakeDetector()
    frames = analyze_frames(video, fps=2.0, detector=fake)
    assert [f.time_s for f in frames] == [0.0, 0.48, 1.0, 1.48]
    assert fake.seen == [(90, 160, 3)] * 4
    assert not fake.closed  # the caller owns a detector it passed in


@needs_ffmpeg
def test_closes_a_detector_it_made(tmp_path, monkeypatch):
    video = make_video(tmp_path / "v.mp4", seconds=1)
    fake = FakeDetector()
    monkeypatch.setattr(analyze_module, "MediaPipeDetector", lambda: fake)
    assert len(analyze_frames(video, fps=1.0)) == 1
    assert fake.closed
