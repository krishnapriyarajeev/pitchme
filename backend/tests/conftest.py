"""Shared fixtures. Integration fixtures skip when their service is down:

make up && uv run pytest -m integration
"""

from __future__ import annotations

import os
import socket
import uuid
from collections.abc import Iterator
from urllib.parse import urlparse

import pytest


def _require(reason: str) -> None:
    """Skip locally, but fail in CI where the services are expected to run."""
    if os.environ.get("CI"):
        pytest.fail(f"{reason} in CI")
    pytest.skip(reason)


def _reachable(url: str, default_port: int) -> bool:
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname, parsed.port or default_port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    """URL of a fresh database migrated to head; dropped after the run."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    from server.config import get_settings

    base = make_url(get_settings().db_url)
    if not _reachable(f"pg://{base.host}:{base.port}", 5432):
        _require("Postgres not reachable (make up)")

    name = f"pitchme_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = base.set(database=name).render_as_string(hide_password=False)
    try:
        yield url
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def storage():
    """Storage client on a throwaway bucket, emptied and removed afterwards."""
    from server.config import Settings
    from server.storage import Storage

    settings = Settings(media_bucket=f"pitchme-test-{uuid.uuid4().hex[:8]}")
    if not _reachable(settings.s3_endpoint, 9000):
        _require("MinIO not reachable (make up)")

    client = Storage(settings)
    client.ensure_bucket()
    try:
        yield client
    finally:
        client.delete_prefix("")
        client._client.remove_bucket(client.bucket)
