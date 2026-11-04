import pytest

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
