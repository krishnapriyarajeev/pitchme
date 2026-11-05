import numpy as np
import pytest

from ai.vision.annotate import (
    AnnotationError,
    VoiceTimeline,
    VoiceWindow,
    _Painter,
    _running_scores,
    draw_badges,
    draw_skeleton,
    draw_voice_panel,
    render_annotated_video,
    voice_timeline,
)
from ai.vision.frames import probe, sample_frames

from .fakes import detection, frames, timeline
from .video import make_video, needs_ffmpeg, streams


def blank(height=480, width=854):
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_skeleton_colour_follows_posture():
    good, bad = blank(), blank()
    draw_skeleton(_Painter(good), frames(1)[0])
    draw_skeleton(_Painter(bad), frames(1, tilt_dy=0.1)[0])
    # Green dominates the good drawing, red the bad one (BGR).
    assert good[..., 1].sum() > good[..., 2].sum()
    assert bad[..., 2].sum() > bad[..., 1].sum()


def test_nothing_drawn_without_a_body():
    image = blank()
    draw_skeleton(_Painter(image), frames(1, body=False)[0])
    assert not image.any()


def test_badges_are_drawn_in_the_corners():
    image = blank()
    draw_badges(_Painter(image), frames(1)[0], "normal")
    assert image[:120, :200].any()  # posture, expression, gestures
    assert image[:50, -190:].any()  # eye contact
    assert not image[200:400, 300:550].any()  # the speaker's middle stays clear


def test_badges_handle_missing_body_and_face():
    image = blank()
    draw_badges(_Painter(image), frames(1, body=False, has_face=False)[0], "unknown")
    assert image.any()


def test_overlays_scale_with_the_video():
    assert _Painter(blank(480)).px(10) == 10
    assert _Painter(blank(1080, 1920)).px(10) == 22
    assert _Painter(blank(240, 320)).px(10) == 6


def test_voice_panel_rows():
    voice = VoiceTimeline((), 150.0, -20.0, (2.75, 6.0), 0.02)
    image = blank()
    draw_voice_panel(_Painter(image), VoiceWindow(0, 15, 150, -21, 4.0, 0.01), voice)
    assert image[48:140, -190:].max() > 100  # text, not just the dark panel
    empty = blank()
    draw_voice_panel(_Painter(empty), VoiceWindow(0, 15), voice)
    assert 0 < empty.max() < 40  # the panel shade with no rows


def test_voice_timeline_lookup():
    voice = VoiceTimeline(
        (VoiceWindow(0, 15, 150), VoiceWindow(10, 25, 160)), 150, -20, (2.75, 6.0), 0.02
    )
    assert voice.at(5).pitch_hz == 150
    assert voice.at(12).pitch_hz == 160  # the latest window wins
    assert voice.at(30) is None


def test_voice_timeline_from_a_voice_report():
    voice = pytest.importorskip("ai.voice")
    from tests.ai.voice.synth import signal, syllables

    report = voice.analyze_voice(signal(syllables(20.0, 4.0)), "qa")
    timeline_ = voice_timeline(report)
    assert timeline_.rate_range == (2.5, 7.0)
    assert [(w.t_start_s, w.t_end_s) for w in timeline_.windows] == [(0.0, 15.0), (10.0, 20.0)]
    assert timeline_.windows[0].rate_sps == pytest.approx(4.0, abs=0.4)


def test_running_scores():
    run = timeline(4, lambda i: detection(looking=i % 2 == 0, tilt_dy=0.1 if i == 3 else 0.0))
    scores = _running_scores(run)
    assert [s.eye_contact for s in scores] == [1.0, 0.5, 2 / 3, 0.5]
    assert scores[-1].posture == 0.75
    assert scores[0].mood == "neutral"
    assert _running_scores(frames(1, body=False, has_face=False))[0].posture is None


@needs_ffmpeg
def test_renders_h264_with_the_original_sound(tmp_path):
    source = make_video(tmp_path / "in.mp4", seconds=2, fps=25, size="320x180", audio=True)
    analyses = frames(4)
    out = render_annotated_video(source, analyses, tmp_path / "out" / "annotated.mp4")
    assert streams(out) == {"video": "h264", "audio": "aac"}
    info = probe(out)
    assert (info.width, info.height) == (320, 180)
    assert info.frame_count == pytest.approx(50, abs=1)

    before = next(sample_frames(source)).bgr
    after = next(sample_frames(out)).bgr
    assert np.abs(after[:60, :100].astype(int) - before[:60, :100]).mean() > 5


@needs_ffmpeg
def test_renders_a_silent_video(tmp_path):
    source = make_video(tmp_path / "in.mp4", seconds=1)
    voice = VoiceTimeline((VoiceWindow(0, 15, 150, -20, 4, 0.01),), 150, -20, (2.75, 6.0), 0.02)
    out = render_annotated_video(source, frames(2), tmp_path / "a.mp4", voice=voice)
    assert streams(out) == {"video": "h264"}


@needs_ffmpeg
def test_missing_ffmpeg(tmp_path, monkeypatch):
    source = make_video(tmp_path / "in.mp4", seconds=1)
    monkeypatch.setattr("ai.vision.annotate.shutil.which", lambda _: None)
    with pytest.raises(AnnotationError, match="ffmpeg is not installed"):
        render_annotated_video(source, frames(2), tmp_path / "a.mp4")
