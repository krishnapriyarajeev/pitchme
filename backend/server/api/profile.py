from __future__ import annotations

from fastapi import APIRouter

from server.deps import CurrentUser, DbSession
from server.deps.storage import StorageDep
from server.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UploadConfirmRequest,
    UploadConfirmResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from server.services import profile as profile_service

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(user: CurrentUser, storage: StorageDep) -> ProfileResponse:
    return profile_service.to_response(user, storage)


@router.put("", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdateRequest, user: CurrentUser, db: DbSession, storage: StorageDep
) -> ProfileResponse:
    return profile_service.to_response(profile_service.update(db, user, body), storage)


@router.post("/upload-url", response_model=UploadUrlResponse)
def create_upload_url(
    body: UploadUrlRequest, user: CurrentUser, storage: StorageDep
) -> UploadUrlResponse:
    """Presigned PUT for the voice sample or the playbook. Confirm after uploading."""
    return profile_service.create_upload_url(user, body.kind, body.file_extension, storage)


@router.post("/upload-confirm", response_model=UploadConfirmResponse)
def confirm_upload(
    body: UploadConfirmRequest, user: CurrentUser, db: DbSession, storage: StorageDep
) -> UploadConfirmResponse:
    """Checks the file landed, belongs to the caller and fits the size limit, then saves it."""
    return profile_service.confirm_upload(db, user, body.kind, body.object_key, storage)
