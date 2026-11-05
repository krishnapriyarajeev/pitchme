"""Domain tables: users and their rehearsal calls."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.db.base import Base, TimestampMixin, uuid_pk


class SessionStatus(enum.StrEnum):
    """Lifecycle of a rehearsal call."""

    waiting = "waiting"  # room created, user not joined yet
    active = "active"  # call in progress
    complete = "complete"  # call ended, transcript saved
    failed = "failed"  # call could not start or the worker crashed


class AnalysisStatus(enum.StrEnum):
    """Lifecycle of the post-call analysis job."""

    not_started = "not_started"
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class VoiceCloneStatus(enum.StrEnum):
    """Cloning the user's voice from their sample, which runs in the background."""

    pending = "pending"
    ready = "ready"
    failed = "failed"


def _pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    display_name: Mapped[str | None]

    # Filled during onboarding; the AI buyer and the content judge use them.
    role_title: Mapped[str | None]
    sells: Mapped[str | None]

    # Object keys in the media bucket, never URLs (URLs expire).
    voice_sample_key: Mapped[str | None]
    voice_transcript: Mapped[str | None]
    voice_clone_id: Mapped[str | None]
    # None until a sample is uploaded.
    voice_clone_status: Mapped[VoiceCloneStatus | None] = mapped_column(
        _pg_enum(VoiceCloneStatus, "voice_clone_status")
    )
    voice_clone_error: Mapped[str | None]
    playbook_key: Mapped[str | None]

    sessions: Mapped[list[PracticeSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class PracticeSession(TimestampMixin, Base):
    """One rehearsal call with the AI buyer, plus its analysis."""

    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    room_name: Mapped[str]
    status: Mapped[SessionStatus] = mapped_column(
        _pg_enum(SessionStatus, "session_status"), default=SessionStatus.waiting
    )

    # Deal details from the prepare screen.
    prospect_name: Mapped[str]
    company: Mapped[str]
    industry: Mapped[str | None]
    deal_stage: Mapped[str]
    buyer_composure: Mapped[str | None]
    competitors: Mapped[str | None]

    # Filled when the call ends. Transcript is a list of {"role", "text"} turns.
    transcript: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    recording_key: Mapped[str | None]
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(9, 2))
    started_at: Mapped[datetime | None]
    ended_at: Mapped[datetime | None]

    # Analysis job state lives in its own columns so a crash or restart can be
    # detected and retried; analysis_data holds only the finished result.
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        _pg_enum(AnalysisStatus, "analysis_status"), default=AnalysisStatus.not_started
    )
    analysis_stage: Mapped[str | None]
    analysis_error: Mapped[str | None]
    analysis_started_at: Mapped[datetime | None]
    analysis_finished_at: Mapped[datetime | None]
    analysis_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    user: Mapped[User] = relationship(back_populates="sessions")
