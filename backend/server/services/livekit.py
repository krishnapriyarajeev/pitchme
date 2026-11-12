"""LiveKit rooms, call recording and join tokens.

The livekit-api client is async; routes and background tasks here are
sync and run in worker threads, so each call runs on its own short event
loop. Tests replace `LiveKitCalls` with a fake through `get_live_calls`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from datetime import timedelta
from typing import Any, Protocol, TypeVar

from livekit import api

from server.config import Settings
from server.errors import DomainError

log = logging.getLogger(__name__)

T = TypeVar("T")

# The recording starts with the room, so its recorder is ready when the
# seller joins. The buyer joins at once and waits two minutes for the
# seller, so the room must not close as empty before that.
EMPTY_TIMEOUT_S = 150


class LiveCallUnavailable(DomainError):
    """Live calls are not available right now. Please try again in a minute."""

    status_code = 503
    code = "live_call_unavailable"


class LiveCalls(Protocol):
    def create_room(self, name: str, metadata: str) -> None: ...
    def start_recording(self, room: str, object_key: str) -> str | None: ...
    def join_token(self, room: str, identity: str, display_name: str) -> str: ...
    def delete_room(self, room: str) -> None: ...


def recording_request(
    room: str, object_key: str, settings: Settings
) -> api.RoomCompositeEgressRequest:
    """Portrait MP4 of the whole room: the seller's camera and both voices.

    The codecs use named values: raw numbers here give H.264 baseline with
    Opus audio, not H.264 main with AAC.
    """
    output = api.EncodedFileOutput(file_type=api.EncodedFileType.MP4, filepath=object_key)
    if settings.egress_s3_endpoint:
        output.s3.CopyFrom(
            api.S3Upload(
                access_key=settings.storage_access_key,
                secret=settings.storage_secret_key,
                endpoint=settings.egress_s3_endpoint,
                region=settings.s3_region,
                bucket=settings.media_bucket,
                force_path_style=True,
            )
        )
    return api.RoomCompositeEgressRequest(
        room_name=room,
        # The phone is held upright; a landscape frame would be mostly padding.
        advanced=api.EncodingOptions(
            width=720,
            height=1280,
            framerate=30,
            video_codec=api.VideoCodec.H264_MAIN,
            audio_codec=api.AudioCodec.AAC,
        ),
        file_outputs=[output],
    )


class LiveKitCalls:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._url = settings.livekit_url.replace("ws://", "http://", 1).replace(
            "wss://", "https://", 1
        )

    def _secret(self) -> str:
        secret = self._settings.livekit_api_secret.get_secret_value()
        if not secret:
            log.error("LIVEKIT_API_SECRET is not set")
            raise LiveCallUnavailable
        return secret

    def _run(self, work: Coroutine[Any, Any, T]) -> T:
        return asyncio.run(work)

    async def _with_api(self, use: Any) -> Any:
        async with api.LiveKitAPI(self._url, self._settings.livekit_api_key, self._secret()) as lk:
            return await use(lk)

    def create_room(self, name: str, metadata: str) -> None:
        request = api.CreateRoomRequest(
            name=name, metadata=metadata, empty_timeout=EMPTY_TIMEOUT_S, departure_timeout=20
        )
        try:
            self._run(self._with_api(lambda lk: lk.room.create_room(request)))
        except LiveCallUnavailable:
            raise
        except Exception as exc:
            log.error("Could not create room %s: %s", name, exc)
            raise LiveCallUnavailable from exc

    def start_recording(self, room: str, object_key: str) -> str | None:
        """The egress id, or None when recording could not start. The call
        goes on without a recording rather than failing."""
        request = recording_request(room, object_key, self._settings)
        try:
            info = self._run(
                self._with_api(lambda lk: lk.egress.start_room_composite_egress(request))
            )
        except Exception as exc:
            log.warning("Could not start recording room %s: %s", room, exc)
            return None
        log.info("Recording room %s to %s (egress %s)", room, object_key, info.egress_id)
        return info.egress_id

    def join_token(self, room: str, identity: str, display_name: str) -> str:
        """Lets one person join one room, valid for LIVEKIT_TOKEN_TTL_MINUTES."""
        return (
            api.AccessToken(self._settings.livekit_api_key, self._secret())
            .with_identity(identity)
            .with_name(display_name)
            .with_grants(api.VideoGrants(room_join=True, room=room))
            .with_ttl(timedelta(minutes=self._settings.livekit_token_ttl_minutes))
            .to_jwt()
        )

    def delete_room(self, room: str) -> None:
        """Ends the call for everyone and stops its recording. A room that
        is already gone is fine."""
        try:
            self._run(
                self._with_api(lambda lk: lk.room.delete_room(api.DeleteRoomRequest(room=room)))
            )
        except Exception as exc:
            log.warning("Could not delete room %s: %s", room, exc)
