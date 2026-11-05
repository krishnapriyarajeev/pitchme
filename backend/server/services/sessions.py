"""Rehearsal calls: create the room, list and show calls, and record what
the agent worker reports.

A call goes waiting -> active (the seller joined) -> complete or failed.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.rehearsal.deal import CallSetup, Deal
from server.config import Settings
from server.db import PracticeSession, SessionStatus, User
from server.errors import Conflict, NotFound
from server.schemas.sessions import (
    CallResults,
    CallStarted,
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetail,
    SessionSummary,
)
from server.services.livekit import LiveCalls
from server.storage import Storage, StorageError
from server.storage.keys import recording_key

log = logging.getLogger(__name__)

# How the call ended -> the session status.
_FINAL_STATUS = {
    "seller_left": SessionStatus.complete,
    "time_limit": SessionStatus.complete,
    "no_show": SessionStatus.failed,
    "error": SessionStatus.failed,
}


# The worker waits this long for the seller to join.
JOIN_WAIT = timedelta(minutes=2)
# Slack for the worker's report to arrive after the call ends.
LOST_MARGIN = timedelta(minutes=5)


def room_name(session_id: uuid.UUID) -> str:
    return f"rehearsal-{session_id}"


def seller_identity(user_id: uuid.UUID) -> str:
    return f"seller-{user_id}"


def create(
    db: Session, user: User, body: CreateSessionRequest, calls: LiveCalls, settings: Settings
) -> CreateSessionResponse:
    """Saves the session, opens its room with the deal in the room metadata
    (the agent worker reads it) and starts recording. If the room cannot be
    made, nothing is saved; if only the recording fails, the call goes on
    without one.

    Recording starts with the room, not when the seller joins: its recorder
    takes about five seconds to start, and started this early it is ready
    and records from about a second after the seller joins."""
    row = PracticeSession(user_id=user.id, room_name="", **body.model_dump())
    db.add(row)
    db.flush()
    row.room_name = room_name(row.id)
    setup = CallSetup(
        session_id=str(row.id),
        seller_identity=seller_identity(user.id),
        deal=Deal(**body.model_dump(), product=user.sells, seller_role=user.role_title),
    )
    try:
        calls.create_room(row.room_name, setup.to_metadata())
        token = calls.join_token(
            row.room_name, setup.seller_identity, user.display_name or "Seller"
        )
    except Exception:
        db.rollback()
        raise
    key = recording_key(user.id, row.id)
    row.egress_id = calls.start_recording(row.room_name, key)
    row.recording_key = key if row.egress_id else None
    db.commit()
    return CreateSessionResponse(
        session_id=row.id,
        room_name=row.room_name,
        token=token,
        livekit_url=settings.livekit_client_url,
    )


def expire_lost(db: Session, rows: Iterable[PracticeSession], settings: Settings) -> None:
    """A call still waiting or active long after the worker would have
    ended it was lost: the worker died before it could report. It is
    marked failed with end_reason "lost" instead of waiting forever."""
    now = datetime.now(UTC)
    cutoff = now - (JOIN_WAIT + timedelta(minutes=settings.rehearsal_max_minutes) + LOST_MARGIN)
    lost = [
        row
        for row in rows
        if row.status in (SessionStatus.waiting, SessionStatus.active) and row.created_at < cutoff
    ]
    for row in lost:
        log.warning("Session %s never reported back; marking it lost", row.id)
        row.status = SessionStatus.failed
        row.end_reason = "lost"
        row.ended_at = now
    if lost:
        db.commit()


def list_for(
    db: Session, user: User, settings: Settings, *, limit: int, offset: int
) -> list[SessionSummary]:
    rows = db.scalars(
        select(PracticeSession)
        .where(PracticeSession.user_id == user.id)
        .order_by(PracticeSession.created_at.desc(), PracticeSession.id)
        .offset(offset)
        .limit(limit)
    ).all()
    expire_lost(db, rows, settings)
    return [to_summary(row) for row in rows]


def get_owned(db: Session, user: User, session_id: uuid.UUID) -> PracticeSession:
    row = db.get(PracticeSession, session_id)
    # Someone else's session is "not found", so ids cannot be probed.
    if row is None or row.user_id != user.id:
        raise NotFound("Session not found.")
    return row


def _duration(row: PracticeSession) -> float | None:
    return round(float(row.duration_seconds), 1) if row.duration_seconds is not None else None


def to_summary(row: PracticeSession) -> SessionSummary:
    return SessionSummary(
        session_id=row.id,
        status=row.status,
        prospect_name=row.prospect_name,
        company=row.company,
        deal_stage=row.deal_stage,
        duration_seconds=_duration(row),
        created_at=row.created_at,
        analysis_status=row.analysis_status,
        overall_score=(row.analysis_data or {}).get("overall_score"),
    )


def _recording_url(row: PracticeSession, storage: Storage) -> str | None:
    """Egress uploads when the call ends, so the key can exist a few
    seconds before the file does."""
    if not row.recording_key:
        return None
    try:
        if not storage.exists(row.recording_key):
            return None
        return storage.presign_download(row.recording_key)
    except StorageError as exc:
        log.warning("Could not check recording %s: %s", row.recording_key, exc)
        return None


def to_detail(row: PracticeSession, storage: Storage) -> SessionDetail:
    return SessionDetail(
        **to_summary(row).model_dump(),
        industry=row.industry,
        buyer_composure=row.buyer_composure,
        competitors=row.competitors,
        audience_type=row.audience_type,
        transcript=row.transcript or [],
        recording_url=_recording_url(row, storage),
        started_at=row.started_at,
        ended_at=row.ended_at,
        end_reason=row.end_reason,
    )


# ---- reports from the agent worker ----


def _get(db: Session, session_id: uuid.UUID) -> PracticeSession:
    row = db.get(PracticeSession, session_id, with_for_update=True)
    if row is None:
        raise NotFound("Session not found.")
    return row


def mark_started(db: Session, session_id: uuid.UUID, body: CallStarted) -> None:
    row = _get(db, session_id)
    if row.status is not SessionStatus.waiting:
        raise Conflict(f"Session is already {row.status}.")
    row.status = SessionStatus.active
    row.started_at = body.started_at
    db.commit()


def record_results(db: Session, session_id: uuid.UUID, body: CallResults) -> None:
    """Saves the transcript and how the call ended. Reported once: a second
    report would overwrite a finished call, so it is refused; a report for
    a call marked lost is still taken, since it is the real outcome. A seller who
    never joined has nothing to play back, so the session gets no recording."""
    row = _get(db, session_id)
    finished = row.status in (SessionStatus.complete, SessionStatus.failed)
    if finished and row.end_reason != "lost":
        raise Conflict(f"Session is already {row.status}.")
    if body.error:
        log.error("Call %s ended with an error: %s", session_id, body.error)
    row.status = _FINAL_STATUS[body.ended_by]
    row.end_reason = body.ended_by
    row.transcript = [turn.model_dump() for turn in body.transcript]
    row.started_at = body.started_at or row.started_at
    row.ended_at = body.ended_at
    row.duration_seconds = body.duration_seconds
    if body.ended_by == "no_show":
        row.recording_key = None
    db.commit()
