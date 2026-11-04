from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

UploadKind = Literal["voice", "playbook"]


class ProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role_title: str | None
    sells: str | None
    has_voice_sample: bool
    voice_sample_url: str | None
    voice_clone_id: str | None
    has_playbook: bool
    playbook_url: str | None
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    """Only the fields sent are changed."""

    display_name: str | None = Field(default=None, max_length=120)
    role_title: str | None = Field(default=None, max_length=120)
    sells: str | None = Field(default=None, max_length=2000)


class UploadUrlRequest(BaseModel):
    kind: UploadKind
    file_extension: str = Field(min_length=1, max_length=10, examples=["m4a", "pdf"])


class UploadUrlResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in_seconds: int


class UploadConfirmRequest(BaseModel):
    kind: UploadKind
    object_key: str = Field(max_length=300)


class UploadConfirmResponse(BaseModel):
    kind: UploadKind
    object_key: str
    url: str
    voice_clone_id: str | None = None
