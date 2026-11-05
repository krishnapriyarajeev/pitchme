"""Profile details and the voice sample / playbook uploads."""

from __future__ import annotations

from sqlalchemy.orm import Session

from server.db import User, VoiceCloneStatus
from server.errors import Forbidden, InvalidUpload, StorageUnavailable
from server.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UploadConfirmResponse,
    UploadKind,
    UploadUrlResponse,
)
from server.storage import Storage, StorageError, keys
from server.storage.client import UPLOAD_TTL


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
        voice_clone_status=user.voice_clone_status,
        voice_clone_error=user.voice_clone_error,
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


# ---- uploads: presign, the app PUTs the file, then confirm ----

MAX_BYTES = {"voice": 20 * 1024 * 1024, "playbook": 25 * 1024 * 1024}

_KEY_FOR = {"voice": keys.profile_voice_key, "playbook": keys.profile_playbook_key}
_KEY_FIELD = {"voice": "voice_sample_key", "playbook": "playbook_key"}


def create_upload_url(
    user: User, kind: UploadKind, ext: str, storage: Storage
) -> UploadUrlResponse:
    try:
        key = _KEY_FOR[kind](user.id, ext)
    except ValueError as exc:
        raise InvalidUpload(str(exc)) from exc
    try:
        url = storage.presign_upload(key)
    except StorageError as exc:
        raise StorageUnavailable() from exc
    return UploadUrlResponse(
        upload_url=url, object_key=key, expires_in_seconds=int(UPLOAD_TTL.total_seconds())
    )


def _expected_key(user: User, kind: UploadKind, object_key: str) -> str:
    """The key must be one this user could have been given for this kind."""
    if not keys.is_owned_by(object_key, user.id):
        raise Forbidden("That file does not belong to you.")
    ext = object_key.rsplit(".", 1)[-1]
    try:
        expected = _KEY_FOR[kind](user.id, ext)
    except ValueError as exc:
        raise InvalidUpload(str(exc)) from exc
    if object_key != expected:
        raise InvalidUpload(f"Not a {kind} upload key.")
    return expected


def confirm_upload(
    db: Session, user: User, kind: UploadKind, object_key: str, storage: Storage
) -> UploadConfirmResponse:
    key = keys.ObjectKey(_expected_key(user, kind, object_key))
    try:
        stat = storage.stat(key)
    except StorageError as exc:
        raise StorageUnavailable() from exc
    if stat is None:
        raise InvalidUpload("No file found; upload it before confirming.")
    if stat.size == 0:
        raise InvalidUpload("The uploaded file is empty.")
    if stat.size > MAX_BYTES[kind]:
        storage.delete_prefix(key)
        raise InvalidUpload(f"File is larger than {MAX_BYTES[kind] // (1024 * 1024)} MB.")

    field = _KEY_FIELD[kind]
    previous = getattr(user, field)
    setattr(user, field, key)
    if kind == "voice":
        # A new sample means the old clone no longer matches. The route
        # starts a background clone from the new one.
        user.voice_clone_id = None
        user.voice_clone_status = VoiceCloneStatus.pending
        user.voice_clone_error = None
        user.voice_transcript = None
    db.commit()

    # Same kind uploaded with another extension: drop the stale file.
    if previous and previous != key:
        storage.delete_prefix(previous)

    return UploadConfirmResponse(
        kind=kind,
        object_key=key,
        url=storage.presign_download(key),
        voice_clone_id=user.voice_clone_id,
        voice_clone_status=user.voice_clone_status,
    )
