from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.db import AnalysisStatus, Base, PracticeSession, SessionStatus, User

pytestmark = pytest.mark.integration

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _alembic(url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    return cfg


@pytest.fixture(scope="module")
def engine(pg_url):
    command.upgrade(_alembic(pg_url), "head")
    eng = create_engine(pg_url)
    yield eng
    eng.dispose()


def test_migration_matches_models(engine):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_downgrade_and_upgrade_round_trip(pg_url, engine):
    command.downgrade(_alembic(pg_url), "base")
    command.upgrade(_alembic(pg_url), "head")


def test_session_defaults_and_cascade(engine):
    with Session(engine) as db:
        user = User(email="kp@example.com", password_hash="x")
        db.add(user)
        db.flush()
        session = PracticeSession(
            user_id=user.id,
            room_name="practice-1",
            prospect_name="Asha",
            company="Acme",
            deal_stage="discovery",
        )
        db.add(session)
        db.commit()

        db.refresh(session)
        assert session.status is SessionStatus.waiting
        assert session.analysis_status is AnalysisStatus.not_started
        assert session.created_at is not None

        db.delete(user)
        db.commit()
        assert db.scalars(select(PracticeSession)).all() == []
