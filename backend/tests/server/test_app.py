import pytest
from fastapi.testclient import TestClient

from server import __version__
from server.config import Settings
from server.main import create_app


def make_client(**overrides) -> TestClient:
    settings = Settings(_env_file=None, log_dir="", **overrides)
    return TestClient(create_app(settings))


def test_health():
    response = make_client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_wildcard_cors_has_no_credentials():
    response = make_client(cors_origins=["*"]).get(
        "/health", headers={"Origin": "http://phone.test"}
    )
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers


@pytest.mark.parametrize(
    ("origin", "allowed"), [("http://app.test", True), ("http://evil.test", False)]
)
def test_explicit_cors_origins(origin, allowed):
    response = make_client(cors_origins=["http://app.test"]).get(
        "/health", headers={"Origin": origin}
    )
    assert ("access-control-allow-origin" in response.headers) is allowed
    if allowed:
        assert response.headers["access-control-allow-credentials"] == "true"
