import jwt
import pytest
from livekit import api

from server.config import Settings
from server.services.livekit import (
    EMPTY_TIMEOUT_S,
    LiveCallUnavailable,
    LiveKitCalls,
    recording_request,
)

SECRET = "s" * 40


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, livekit_api_secret=SECRET, **overrides)


def test_recording_is_portrait_h264_main_with_aac():
    request = recording_request("rehearsal-1", "users/u/sessions/s/recording.mp4", settings())
    assert request.room_name == "rehearsal-1"
    assert (request.advanced.width, request.advanced.height) == (720, 1280)
    assert request.advanced.video_codec == api.VideoCodec.H264_MAIN
    assert request.advanced.audio_codec == api.AudioCodec.AAC
    (output,) = request.file_outputs
    assert output.file_type == api.EncodedFileType.MP4
    assert output.filepath == "users/u/sessions/s/recording.mp4"
    # Uploads with the egress service's own storage config.
    assert not output.HasField("s3")


def test_recording_uploads_to_an_explicit_endpoint_when_set():
    request = recording_request(
        "r",
        "k.mp4",
        settings(
            egress_s3_endpoint="http://storage:9000",
            s3_access_key="ak",
            s3_secret_key="sk",
            media_bucket="media",
        ),
    )
    s3 = request.file_outputs[0].s3
    assert (s3.endpoint, s3.access_key, s3.secret, s3.bucket) == (
        "http://storage:9000",
        "ak",
        "sk",
        "media",
    )
    assert s3.force_path_style


def test_join_token_admits_one_identity_to_one_room():
    token = LiveKitCalls(settings(livekit_token_ttl_minutes=5)).join_token(
        "rehearsal-1", "seller-1", "Sam"
    )
    claims = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_aud": False})
    assert claims["sub"] == "seller-1"
    assert claims["name"] == "Sam"
    assert claims["video"]["room"] == "rehearsal-1"
    assert claims["video"]["roomJoin"] is True
    assert claims["exp"] - claims["nbf"] == 5 * 60


def test_missing_secret_is_unavailable_not_a_crash():
    calls = LiveKitCalls(Settings(_env_file=None, livekit_api_secret=""))
    with pytest.raises(LiveCallUnavailable):
        calls.join_token("r", "i", "n")
    with pytest.raises(LiveCallUnavailable):
        calls.create_room("r", "{}")
    assert calls.start_recording("r", "k.mp4") is None


def test_unreachable_livekit_is_unavailable():
    calls = LiveKitCalls(settings(livekit_url="ws://127.0.0.1:9"))
    with pytest.raises(LiveCallUnavailable):
        calls.create_room("r", "{}")
    assert calls.start_recording("r", "k.mp4") is None
    calls.delete_room("r")  # logged, not raised


def test_rooms_outlive_the_buyers_wait_for_the_seller():
    agent = pytest.importorskip("ai.rehearsal.agent", reason="needs the rehearsal extra")
    JOIN_TIMEOUT_S = agent.JOIN_TIMEOUT_S

    assert EMPTY_TIMEOUT_S > JOIN_TIMEOUT_S
