"""LiveKitCalls against the LiveKit and Egress from `make up`.

Room and token tests run with the integration tests and skip when LiveKit
is not running. The recording test is slower and runs with make test-live;
egress can only reach LiveKit when LAN_IP is set (make practice sets it).
"""

import asyncio
import math
import time
import uuid

import pytest

from server.config import Settings
from server.services.livekit import LiveKitCalls
from tests.conftest import _reachable

rtc = pytest.importorskip("livekit.rtc", reason="needs the rehearsal extra")
np = pytest.importorskip("numpy")

pytestmark = pytest.mark.integration


@pytest.fixture
def settings():
    settings = Settings()
    if not settings.livekit_api_secret.get_secret_value():
        pytest.skip("LIVEKIT_API_SECRET is not set")
    if not _reachable(settings.livekit_url.replace("ws", "http", 1), 7880):
        pytest.skip("LiveKit not reachable (make up)")
    return settings


async def _join_and_publish(url: str, token: str, seconds: float) -> rtc.Room:
    """Join as the seller with a tone and a grey camera, like a phone would."""
    room = rtc.Room()
    await room.connect(url, token)
    audio = rtc.AudioSource(48_000, 1)
    video = rtc.VideoSource(360, 640)
    options = rtc.TrackPublishOptions
    await room.local_participant.publish_track(
        rtc.LocalAudioTrack.create_audio_track("mic", audio),
        options(source=rtc.TrackSource.SOURCE_MICROPHONE),
    )
    await room.local_participant.publish_track(
        rtc.LocalVideoTrack.create_video_track("camera", video),
        options(source=rtc.TrackSource.SOURCE_CAMERA),
    )
    frame = np.full((640, 360, 4), 128, np.uint8).tobytes()
    start, n = time.monotonic(), 0
    while time.monotonic() - start < seconds:
        t = np.arange(480) + n * 480
        pcm = (np.sin(2 * math.pi * 220 * t / 48_000) * 8000).astype(np.int16)
        await audio.capture_frame(rtc.AudioFrame(pcm.tobytes(), 48_000, 1, 480))
        if n % 3 == 0:
            video.capture_frame(rtc.VideoFrame(360, 640, rtc.VideoBufferType.RGBA, frame))
        n += 1
        await asyncio.sleep(0.01)
    return room


def test_room_carries_metadata_and_admits_the_token(settings):
    calls = LiveKitCalls(settings)
    name = f"test-{uuid.uuid4().hex[:8]}"
    calls.create_room(name, '{"kind": "test"}')
    token = calls.join_token(name, "seller-test", "Tester")

    async def join():
        room = rtc.Room()
        await room.connect(settings.livekit_url, token)
        try:
            return room.name, room.metadata, room.local_participant.identity
        finally:
            await room.disconnect()

    try:
        assert asyncio.run(join()) == (name, '{"kind": "test"}', "seller-test")
    finally:
        calls.delete_room(name)
    calls.delete_room(name)  # already gone: no error


@pytest.mark.live
def test_recording_lands_in_storage(settings):
    from server.storage import Storage

    calls = LiveKitCalls(settings)
    media = Storage(settings)  # egress writes to the real media bucket
    name = f"test-{uuid.uuid4().hex[:8]}"
    prefix = f"users/test-{name}/"
    key = f"{prefix}sessions/s/recording.mp4"
    calls.create_room(name, "{}")
    try:
        assert calls.start_recording(name, key)
        token = calls.join_token(name, "seller-test", "Tester")

        async def call():
            room = await _join_and_publish(settings.livekit_url, token, 8)
            await room.disconnect()

        asyncio.run(call())
    finally:
        calls.delete_room(name)
    try:
        for _ in range(30):
            if media.exists(key):
                break
            time.sleep(1)
        stat = media.stat(key)
        assert stat is not None, "no recording; is LAN_IP set for the LiveKit container?"
        assert stat.size > 20_000
    finally:
        media.delete_prefix(prefix)
