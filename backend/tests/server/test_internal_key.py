import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.config import Settings, get_settings
from server.deps.internal import InternalCaller
from server.errors import install_error_handlers


def make_client(key: str) -> TestClient:
    app = FastAPI()
    install_error_handlers(app)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, ai_callback_key=key)

    @app.post("/internal/ping", dependencies=[InternalCaller])
    def ping():
        return {"ok": True}

    return TestClient(app)


def test_correct_key_passes():
    response = make_client("k" * 32).post("/internal/ping", headers={"X-Internal-Key": "k" * 32})
    assert response.status_code == 200


@pytest.mark.parametrize("header", [None, "", "wrong"])
def test_wrong_or_missing_key_is_forbidden(header):
    headers = {} if header is None else {"X-Internal-Key": header}
    response = make_client("k" * 32).post("/internal/ping", headers=headers)
    assert response.status_code == 403


def test_unset_server_key_rejects_everything():
    response = make_client("").post("/internal/ping", headers={"X-Internal-Key": ""})
    assert response.status_code == 403
