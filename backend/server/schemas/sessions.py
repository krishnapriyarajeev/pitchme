from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai.rehearsal.deal import AUDIENCES, COMPOSURES, STAGES, normalize

SessionState = Literal["waiting", "active", "complete", "failed"]
EndReason = Literal["seller_left", "time_limit", "no_show", "error"]


class CreateSessionRequest(BaseModel):
    """The deal from the prepare screen. Choices accept the app's labels
    ("Cold call", "VP Sales") and are stored as keys ("cold_call")."""

    model_config = ConfigDict(str_strip_whitespace=True)

    prospect_name: str = Field(min_length=1, max_length=120, examples=["Jo Bennett"])
    company: str = Field(min_length=1, max_length=120, examples=["Saber Industries"])
    industry: str | None = Field(default=None, max_length=120)
    deal_stage: str = Field(default="discovery", examples=list(STAGES))
    buyer_composure: str | None = Field(default=None, examples=list(COMPOSURES))
    competitors: str | None = Field(default=None, max_length=300)
    audience_type: str = Field(default="general", examples=list(AUDIENCES))

    @field_validator("industry", "competitors")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("deal_stage")
    @classmethod
    def _stage(cls, value: str) -> str:
        return normalize(value, STAGES, "deal stage")

    @field_validator("buyer_composure")
    @classmethod
    def _composure(cls, value: str | None) -> str | None:
        return normalize(value, COMPOSURES, "composure") if value else None

    @field_validator("audience_type")
    @classmethod
    def _audience(cls, value: str) -> str:
        return normalize(value or "general", AUDIENCES, "audience")


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    room_name: str
    # Join the room with this token within LIVEKIT_TOKEN_TTL_MINUTES.
    token: str
    livekit_url: str


class TranscriptTurn(BaseModel):
    role: Literal["seller", "buyer"]
    text: str = Field(max_length=10_000)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    interrupted: bool = False


class SessionSummary(BaseModel):
    session_id: uuid.UUID
    status: SessionState
    prospect_name: str
    company: str
    deal_stage: str
    duration_seconds: float | None
    created_at: datetime
    analysis_status: str
    overall_score: float | None = None


class SessionDetail(SessionSummary):
    industry: str | None
    buyer_composure: str | None
    competitors: str | None
    audience_type: str | None
    transcript: list[TranscriptTurn]
    # Presigned; None until the recording is in storage.
    recording_url: str | None
    started_at: datetime | None
    ended_at: datetime | None
    end_reason: EndReason | None


# ---- from the agent worker ----


class CallStarted(BaseModel):
    started_at: datetime


class CallResults(BaseModel):
    transcript: list[TranscriptTurn] = Field(default_factory=list, max_length=2000)
    ended_by: EndReason
    started_at: datetime | None = None
    ended_at: datetime
    duration_seconds: float | None = Field(default=None, ge=0)
    error: str | None = Field(default=None, max_length=2000)
