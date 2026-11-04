import pytest

pytestmark = pytest.mark.integration

USER = {"email": "Asha@Example.com", "password": "rehearse-daily", "display_name": "Asha"}


def test_register_returns_token(api):
    response = api.post("/api/auth/register", json=USER)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user_id"]


def test_duplicate_email_is_case_insensitive(api):
    api.post("/api/auth/register", json=USER)
    response = api.post("/api/auth/register", json={**USER, "email": "asha@example.com"})
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


@pytest.mark.parametrize(
    "body",
    [
        {**USER, "password": "short"},
        {**USER, "email": "not-an-email"},
    ],
)
def test_register_validation(api, body):
    assert api.post("/api/auth/register", json=body).status_code == 422


def test_login(api):
    user_id = api.post("/api/auth/register", json=USER).json()["user_id"]
    response = api.post(
        "/api/auth/login", json={"email": "asha@example.com", "password": USER["password"]}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id


@pytest.mark.parametrize(
    "creds",
    [
        {"email": USER["email"], "password": "wrong-password"},
        {"email": "nobody@example.com", "password": USER["password"]},
    ],
)
def test_login_rejects_bad_credentials(api, creds):
    api.post("/api/auth/register", json=USER)
    response = api.post("/api/auth/login", json=creds)
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_token_form_login(api):
    api.post("/api/auth/register", json=USER)
    response = api.post(
        "/api/auth/token", data={"username": USER["email"], "password": USER["password"]}
    )
    assert response.status_code == 200
