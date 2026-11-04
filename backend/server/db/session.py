"""Engine, session factory and the FastAPI database dependency."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from server.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping drops connections Postgres closed while the API was idle.
    return create_engine(get_settings().db_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: `db: Session = Depends(get_db)`."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
