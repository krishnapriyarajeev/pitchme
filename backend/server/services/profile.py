"""Profile details and the voice sample / playbook uploads."""

from __future__ import annotations

from sqlalchemy.orm import Session

from server.db import User
from server.schemas.profile import ProfileResponse, ProfileUpdateRequest
from server.storage import Storage


def to_response(user: User, storage: Storage) -> ProfileResponse:
    return ProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_title=user.role_title,
        sells=user.sells,
        has_voice_sample=user.voice_sample_key is not None,
        voice_sample_url=storage.presign_download(user.voice_sample_key)
        if user.voice_sample_key
        else None,
        voice_clone_id=user.voice_clone_id,
        has_playbook=user.playbook_key is not None,
        playbook_url=storage.presign_download(user.playbook_key) if user.playbook_key else None,
        created_at=user.created_at,
    )


def update(db: Session, user: User, changes: ProfileUpdateRequest) -> User:
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(user, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(user)
    return user
