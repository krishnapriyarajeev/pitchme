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
def voice_client():
    """The voice provider every API test clones with; never a real one."""
    from tests.ai.voice_cloning.fakes import FakeVoiceClient

    return FakeVoiceClient()


class FakeLiveCalls:
    """Stands in for LiveKit: records what the API asked for."""

    def __init__(self):
        self.rooms, self.recordings, self.deleted = {}, [], []
        self.fail_create = self.fail_recording = False

    def create_room(self, name, metadata):
        from server.services.livekit import LiveCallUnavailable

        if self.fail_create:
            raise LiveCallUnavailable
        self.rooms[name] = metadata

    def start_recording(self, room, object_key):
        if self.fail_recording:
            return None
        self.recordings.append((room, object_key))
        return f"EG_{len(self.recordings)}"

    def join_token(self, room, identity, display_name):
        return f"token:{room}:{identity}:{display_name}"

    def delete_room(self, room):
        self.deleted.append(room)


@pytest.fixture
def live_calls():
    return FakeLiveCalls()


CALLBACK_KEY = "test-callback-key-" + "c" * 32


@pytest.fixture
def api(db_sessionmaker, storage, voice_client, live_calls, monkeypatch) -> TestClient:
    from server.config import Settings, get_settings
    from server.db.session import get_db
    from server.deps.livekit import get_live_calls
    from server.deps.voice_clone import get_voice_cloner
    from server.main import create_app
    from server.services.voice_clone import VoiceCloner
    from server.storage import get_storage

    settings = Settings(
        log_dir="",
        jwt_secret="test-jwt-secret-" + "z" * 32,
        ai_callback_key=CALLBACK_KEY,
        livekit_public_url="ws://192.168.1.5:7880",
    )
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
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_live_calls] = lambda: live_calls
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_voice_cloner] = lambda: VoiceCloner(
        db_sessionmaker, storage, client_factory=lambda: voice_client
    )
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
