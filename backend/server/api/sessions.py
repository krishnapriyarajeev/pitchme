from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from rq import Queue

from server.config import Settings, get_settings
from server.deps import CurrentUser, DbSession
from server.deps.livekit import LiveCallsDep
from server.deps.storage import StorageDep
from server.jobs.queue import get_analysis_queue
from server.schemas.analysis import AnalysisResponse, AnalysisStatusResponse, AnalyzeRequest
from server.schemas.sessions import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionDetail,
    SessionSummary,
)
from server.services import analysis as analysis_service
from server.services import sessions as session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    body: CreateSessionRequest,
    user: CurrentUser,
    db: DbSession,
    calls: LiveCallsDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CreateSessionResponse:
    """Opens a call with the AI buyer. Join the returned room with the token;
    the buyer joins on its own and speaks first."""
    return session_service.create(db, user, body, calls, settings)


@router.get("", response_model=list[SessionSummary])
def list_sessions(
    user: CurrentUser,
    db: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SessionSummary]:
    """The caller's sessions, newest first."""
    return session_service.list_for(db, user, settings, limit=limit, offset=offset)


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionDetail:
    row = session_service.get_owned(db, user, session_id)
    session_service.expire_lost(db, [row], settings)
    return session_service.to_detail(row, storage)


@router.post(
    "/{session_id}/analyze",
    response_model=AnalysisStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_session(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    queue: Annotated[Queue, Depends(get_analysis_queue)],
    settings: Annotated[Settings, Depends(get_settings)],
    body: AnalyzeRequest | None = None,
) -> AnalysisStatusResponse:
    """Queues the analysis of a finished call; poll the analysis for
    progress. Running it again replaces the last result."""
    row = session_service.get_owned(db, user, session_id)
    return analysis_service.request(db, row, queue, settings, (body or AnalyzeRequest()).mode)


@router.get("/{session_id}/analysis", response_model=AnalysisResponse)
def get_analysis(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnalysisResponse:
    """Status and stage while it runs; the full result once complete."""
    row = session_service.get_owned(db, user, session_id)
    return analysis_service.read(db, row, storage, settings)
