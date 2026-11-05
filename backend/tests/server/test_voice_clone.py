"""Cloning the voice after a sample upload, against real Postgres and MinIO
with a fake voice provider."""

import shutil
import subprocess

import httpx
import pytest

from ai.voice_cloning.base import VoiceCloneError
from server.db import User, VoiceCloneStatus
from server.services.voice_clone import UNAVAILABLE, UNREADABLE, VoiceCloner

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed"),
]


@pytest.fixture(scope="module")
def m4a(tmp_path_factory) -> bytes:
    """Two seconds of tone recorded as AAC, like a phone sample."""
    path = tmp_path_factory.mktemp("voice") / "sample.m4a"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=180:duration=2",
            "-c:a", "aac", str(path),
        ],
        check=True,
    )  # fmt: skip
    return path.read_bytes()


def _upload_voice(client, content: bytes, ext: str = "m4a") -> dict:
    presign = client.post("/api/profile/upload-url", json={"kind": "voice", "file_extension": ext})
    body = presign.json()
    assert httpx.put(body["upload_url"], content=content).status_code == 200
    return client.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": body["object_key"]}
    ).json()


def test_upload_clones_the_voice_from_a_wav_copy(signed_in, voice_client, m4a):
    confirm = _upload_voice(signed_in, m4a)
    assert confirm["voice_clone_status"] == "pending"

    profile = signed_in.get("/api/profile").json()
    assert profile["voice_clone_status"] == "ready"
    assert profile["voice_clone_id"] == "voice-1"
    assert profile["voice_clone_error"] is None
    ((sample, name),) = voice_client.cloned
    assert str(sample.audio_path).endswith(".wav")
    assert name.startswith("pitchme-")


def test_new_sample_replaces_and_deletes_the_old_clone(signed_in, voice_client, m4a):
    _upload_voice(signed_in, m4a)
    _upload_voice(signed_in, m4a, ext="mp3")  # ffmpeg reads the real format
    profile = signed_in.get("/api/profile").json()
    assert profile["voice_clone_id"] == "voice-2"
    assert voice_client.deleted == ["voice-1"]


def test_unreadable_sample_fails_with_a_plain_message(signed_in, voice_client):
    _upload_voice(signed_in, b"not audio at all")
    profile = signed_in.get("/api/profile").json()
    assert profile["voice_clone_status"] == "failed"
    assert profile["voice_clone_error"] == UNREADABLE
    assert profile["voice_clone_id"] is None
    assert voice_client.cloned == []


def test_provider_failure_leaves_no_placeholder_id(signed_in, db_sessionmaker, storage, m4a, api):
    from server.deps.voice_clone import get_voice_cloner

    def broken():
        raise VoiceCloneError("CARTESIA_API_KEY is not set.")

    api.app.dependency_overrides[get_voice_cloner] = lambda: VoiceCloner(
        db_sessionmaker, storage, client_factory=broken
    )
    _upload_voice(signed_in, m4a)
    profile = signed_in.get("/api/profile").json()
    assert profile["voice_clone_status"] == "failed"
    assert profile["voice_clone_error"] == UNAVAILABLE  # the key name stays in the log
    assert profile["voice_clone_id"] is None


def test_retry_needs_a_sample_then_clones_again(signed_in, voice_client, m4a):
    response = signed_in.post("/api/profile/voice-clone")
    assert response.status_code == 422

    _upload_voice(signed_in, m4a)
    response = signed_in.post("/api/profile/voice-clone")
    assert response.status_code == 202
    assert response.json() == {"status": "pending", "error": None}
    assert signed_in.get("/api/profile").json()["voice_clone_id"] == "voice-2"
    assert voice_client.deleted == ["voice-1"]


def test_late_clone_for_a_replaced_sample_is_thrown_away(
    signed_in, db_sessionmaker, storage, voice_client, m4a
):
    first = _upload_voice(signed_in, m4a)
    with db_sessionmaker() as db:
        user = db.query(User).one()
        user.voice_sample_key = "users/other/profile/voice.m4a"  # a newer upload
        user.voice_clone_id = None
        user.voice_clone_status = VoiceCloneStatus.pending
        db.commit()
        user_id = user.id

    VoiceCloner(db_sessionmaker, storage, client_factory=lambda: voice_client)(
        user_id, first["object_key"], "voice-1"
    )
    with db_sessionmaker() as db:
        user = db.get(User, user_id)
        assert user.voice_clone_id is None
        assert user.voice_clone_status is VoiceCloneStatus.pending
    # Both the late clone and the one it would have replaced are removed.
    assert voice_client.deleted == ["voice-2", "voice-1"]
