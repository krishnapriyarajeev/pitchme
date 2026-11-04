"""API test client on a real, migrated Postgres database."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def alembic_config(url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    return cfg


@pytest.fixture(scope="session")
def db_engine(pg_url):
    command.upgrade(alembic_config(pg_url), "head")
    engine = create_engine(pg_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_sessionmaker(db_engine):
    yield sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    with db_engine.begin() as conn:
        conn.execute(text("TRUNCATE users CASCADE"))


@pytest.fixture
def api(db_sessionmaker, storage, monkeypatch) -> TestClient:
    from server.config import Settings, get_settings
    from server.db.session import get_db
    from server.main import create_app
    from server.storage import get_storage

    settings = Settings(log_dir="", jwt_secret="test-jwt-secret-" + "z" * 32)
    monkeypatch.setattr("server.security.get_settings", lambda: settings)
    get_settings.cache_clear()

    def _db():
        db = db_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    app = create_app(settings)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_storage] = lambda: storage
    return TestClient(app)


@pytest.fixture
def signed_in(api) -> TestClient:
    """Client with a registered user's bearer token set."""
    response = api.post(
        "/api/auth/register",
        json={"email": "kp@example.com", "password": "rehearse-daily", "display_name": "KP"},
    )
    api.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return api
