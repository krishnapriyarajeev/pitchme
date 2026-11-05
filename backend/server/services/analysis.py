"""Start an analysis and read its progress and result.

A job that dies without saying so (the worker was killed, Redis lost it)
would leave the session queued or running forever; reading the status
notices that and marks it failed, so the user can run it again.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from rq import Callback, Queue
from sqlalchemy.orm import Session

from server.config import Settings
from server.db import AnalysisStatus, PracticeSession, SessionStatus
from server.errors import Conflict, DomainError
from server.jobs.analysis import on_job_failure, run_session_analysis
from server.schemas.analysis import (
    AnalysisMode,
    AnalysisResponse,
    AnalysisResult,
    AnalysisStatusResponse,
)
from server.storage import Storage, StorageError

log = logging.getLogger(__name__)

# A queued job no worker has taken by then is given up on.
QUEUE_WAIT = timedelta(minutes=10)
NOT_STARTED = "The analysis did not start. Check that the worker is running, then try again."
STOPPED = "The analysis stopped unexpectedly. Run it again."

_ACTIVE = (AnalysisStatus.queued, AnalysisStatus.running)


class AnalysisUnavailable(DomainError):
    """Analysis is not available right now. Please try again in a minute."""

    status_code = 503
    code = "analysis_unavailable"


def _now() -> datetime:
    return datetime.now(UTC)


def expire_stale(db: Session, row: PracticeSession, settings: Settings) -> None:
    now = _now()
    if row.analysis_status is AnalysisStatus.queued and row.updated_at < now - QUEUE_WAIT:
        error = NOT_STARTED
    elif row.analysis_status is AnalysisStatus.running and (
        row.analysis_started_at is None
        or row.analysis_started_at < now - timedelta(minutes=settings.analysis_timeout_minutes + 5)
    ):
        error = STOPPED
    else:
        return
    row.analysis_status = AnalysisStatus.failed
    row.analysis_stage = None
    row.analysis_error = error
    row.analysis_finished_at = now
    db.commit()


def to_status(row: PracticeSession) -> AnalysisStatusResponse:
    return AnalysisStatusResponse(
        status=row.analysis_status,
        stage=row.analysis_stage,
        error=row.analysis_error,
        started_at=row.analysis_started_at,
        finished_at=row.analysis_finished_at,
    )


def request(
    db: Session, row: PracticeSession, queue: Queue, settings: Settings, mode: AnalysisMode
) -> AnalysisStatusResponse:
    """Queue an analysis of a finished call. While one is queued or running
    this returns its status instead of starting a second."""
    if row.status is not SessionStatus.complete:
        raise Conflict("Only a finished call can be analysed.")
    expire_stale(db, row, settings)
    if row.analysis_status in _ACTIVE:
        return to_status(row)

    previous = (row.analysis_status, row.analysis_error)
    row.analysis_status = AnalysisStatus.queued
    row.analysis_stage = None
    row.analysis_error = None
    row.analysis_finished_at = None
    db.commit()
    try:
        queue.enqueue(
            run_session_analysis,
            args=(str(row.id), mode),
            job_timeout=settings.analysis_timeout_minutes * 60,
            result_ttl=0,
            failure_ttl=24 * 3600,
            on_failure=Callback(on_job_failure),
        )
    except Exception as exc:
        log.error("Could not queue the analysis of %s: %s", row.id, exc)
        row.analysis_status, row.analysis_error = previous
        db.commit()
        raise AnalysisUnavailable from exc
    db.refresh(row)
    return to_status(row)


def _url(key: str | None, storage: Storage) -> str | None:
    if not key:
        return None
    try:
        return storage.presign_download(key)
    except StorageError as exc:
        log.warning("Could not sign %s: %s", key, exc)
        return None


def _result(data: dict[str, Any], storage: Storage) -> AnalysisResult:
    """Stored keys become fresh links; links are never stored, they expire."""
    answers = [
        {
            **{k: v for k, v in a.items() if k != "audio_key"},
            "audio_url": _url(a.get("audio_key"), storage),
        }
        for a in data.get("corrected_answers", [])
    ]
    return AnalysisResult(
        **{k: v for k, v in data.items() if k not in ("corrected_answers", "annotated_video_key")},
        corrected_answers=answers,
        annotated_video_url=_url(data.get("annotated_video_key"), storage),
    )


def read(
    db: Session, row: PracticeSession, storage: Storage, settings: Settings
) -> AnalysisResponse:
    expire_stale(db, row, settings)
    complete = row.analysis_status is AnalysisStatus.complete and row.analysis_data
    return AnalysisResponse(
        **to_status(row).model_dump(),
        result=_result(row.analysis_data, storage) if complete else None,
    )
