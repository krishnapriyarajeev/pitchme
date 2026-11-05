"""Calls from the LiveKit agent worker, checked with AI_CALLBACK_KEY."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from server.deps import DbSession
from server.deps.internal import InternalCaller
from server.schemas.sessions import CallResults, CallStarted
from server.services import sessions as session_service

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[InternalCaller])


@router.post("/sessions/{session_id}/started", status_code=status.HTTP_204_NO_CONTENT)
def call_started(session_id: uuid.UUID, body: CallStarted, db: DbSession) -> None:
    """The seller joined: the call is active."""
    session_service.mark_started(db, session_id, body)


@router.post("/sessions/{session_id}/results", status_code=status.HTTP_204_NO_CONTENT)
def call_results(session_id: uuid.UUID, body: CallResults, db: DbSession) -> None:
    """The call ended: transcript, timing and how it ended."""
    session_service.record_results(db, session_id, body)
