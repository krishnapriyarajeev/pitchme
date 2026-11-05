import httpx
import pytest

from server.services import profile as profile_service

pytestmark = pytest.mark.integration


def test_profile_requires_sign_in(api):
    response = api.get("/api/profile")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_bad_token_is_401(api):
    response = api.get("/api/profile", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_get_profile(signed_in):
    body = signed_in.get("/api/profile").json()
    assert body["email"] == "kp@example.com"
    assert body["display_name"] == "KP"
    assert body["has_voice_sample"] is False
    assert body["voice_sample_url"] is None
    assert body["has_playbook"] is False


def test_partial_update_keeps_other_fields(signed_in):
    response = signed_in.put(
        "/api/profile", json={"role_title": "  Account Executive ", "sells": "Payroll software"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role_title"] == "Account Executive"
    assert body["sells"] == "Payroll software"
    assert body["display_name"] == "KP"

    body = signed_in.put("/api/profile", json={"display_name": "Krishnapriya"}).json()
    assert body["display_name"] == "Krishnapriya"
    assert body["sells"] == "Payroll software"


def _upload(client, kind, ext, content: bytes) -> dict:
    presign = client.post("/api/profile/upload-url", json={"kind": kind, "file_extension": ext})
    assert presign.status_code == 200
    body = presign.json()
    assert httpx.put(body["upload_url"], content=content).status_code == 200
    return body


def test_voice_upload_flow(signed_in):
    body = _upload(signed_in, "voice", "m4a", b"fake-m4a-audio")
    assert body["object_key"].endswith("/profile/voice.m4a")
    assert body["expires_in_seconds"] == 3600

    confirm = signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": body["object_key"]}
    )
    assert confirm.status_code == 200
    assert confirm.json()["voice_clone_status"] == "pending"
    assert httpx.get(confirm.json()["url"]).content == b"fake-m4a-audio"

    profile = signed_in.get("/api/profile").json()
    assert profile["has_voice_sample"] is True
    assert profile["voice_sample_url"]
    # These bytes are not audio, so the background clone fails cleanly.
    assert profile["voice_clone_status"] == "failed"


def test_reupload_with_new_extension_removes_old_file(signed_in, storage):
    old = _upload(signed_in, "voice", "m4a", b"old")
    signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": old["object_key"]}
    )
    new = _upload(signed_in, "voice", "wav", b"new")
    signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": new["object_key"]}
    )

    assert not storage.exists(old["object_key"])
    assert storage.exists(new["object_key"])


def test_playbook_upload_flow(signed_in):
    body = _upload(signed_in, "playbook", "pdf", b"%PDF-1.7 playbook")
    confirm = signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "playbook", "object_key": body["object_key"]}
    )
    assert confirm.status_code == 200
    assert signed_in.get("/api/profile").json()["has_playbook"] is True


def test_unsupported_extension(signed_in):
    response = signed_in.post(
        "/api/profile/upload-url", json={"kind": "voice", "file_extension": "exe"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_upload"


def test_confirm_before_upload(signed_in):
    body = signed_in.post(
        "/api/profile/upload-url", json={"kind": "voice", "file_extension": "wav"}
    ).json()
    response = signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": body["object_key"]}
    )
    assert response.status_code == 422
    assert "upload it before confirming" in response.json()["detail"]


def test_confirm_empty_file(signed_in):
    body = _upload(signed_in, "voice", "wav", b"")
    response = signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": body["object_key"]}
    )
    assert response.status_code == 422


def test_cannot_claim_another_users_file(signed_in, storage):
    other_key = "users/00000000-0000-0000-0000-000000000000/profile/voice.wav"
    storage.put_bytes(other_key, b"someone else", "audio/wav")
    response = signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": other_key}
    )
    assert response.status_code == 403


def test_kind_must_match_key(signed_in):
    body = _upload(signed_in, "playbook", "pdf", b"%PDF")
    response = signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": body["object_key"]}
    )
    assert response.status_code == 422


def test_oversized_upload_is_rejected_and_removed(signed_in, storage, monkeypatch):
    monkeypatch.setitem(profile_service.MAX_BYTES, "voice", 4)
    body = _upload(signed_in, "voice", "wav", b"too big")
    response = signed_in.post(
        "/api/profile/upload-confirm", json={"kind": "voice", "object_key": body["object_key"]}
    )
    assert response.status_code == 422
    assert not storage.exists(body["object_key"])
