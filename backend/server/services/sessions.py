"""Rehearsal calls: create the room, list and show calls, and record what
the agent worker reports.

A call goes waiting -> active (the seller joined) -> complete or failed.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.rehearsal.deal import CallSetup, Deal
from server.config import Settings
from server.db import PracticeSession, User
from server.errors import NotFound
from server.schemas.sessions import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetail,
    SessionSummary,
)
from server.services.livekit import LiveCalls
from server.storage import Storage, StorageError
from server.storage.keys import recording_key

log = logging.getLogger(__name__)


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


def list_for(db: Session, user: User, *, limit: int, offset: int) -> list[SessionSummary]:
    rows = db.scalars(
        select(PracticeSession)
        .where(PracticeSession.user_id == user.id)
        .order_by(PracticeSession.created_at.desc(), PracticeSession.id)
        .offset(offset)
        .limit(limit)
    )
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
