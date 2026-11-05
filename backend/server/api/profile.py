from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status

from server.deps import CurrentUser, DbSession
from server.deps.storage import StorageDep
from server.deps.voice_clone import VoiceClonerDep
from server.errors import InvalidUpload
from server.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    UploadConfirmRequest,
    UploadConfirmResponse,
    UploadUrlRequest,
    UploadUrlResponse,
    VoiceCloneResponse,
)
from server.services import profile as profile_service
from server.services.voice_clone import mark_pending

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
    body: UploadConfirmRequest,
    user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
    cloner: VoiceClonerDep,
    background: BackgroundTasks,
) -> UploadConfirmResponse:
    """Checks the file landed, belongs to the caller and fits the size limit, then saves it.

    A voice sample also starts cloning the voice in the background; watch
    `voice_clone_status` on the profile.
    """
    previous_clone = user.voice_clone_id
    result = profile_service.confirm_upload(db, user, body.kind, body.object_key, storage)
    if body.kind == "voice":
        background.add_task(cloner, user.id, result.object_key, previous_clone)
    return result


@router.post(
    "/voice-clone", response_model=VoiceCloneResponse, status_code=status.HTTP_202_ACCEPTED
)
def retry_voice_clone(
    user: CurrentUser, db: DbSession, cloner: VoiceClonerDep, background: BackgroundTasks
) -> VoiceCloneResponse:
    """Clone the voice again from the current sample, for example after a failure."""
    if not user.voice_sample_key:
        raise InvalidUpload("Upload a voice sample first.")
    previous_clone = mark_pending(db, user)
    background.add_task(cloner, user.id, user.voice_sample_key, previous_clone)
    return VoiceCloneResponse(status=user.voice_clone_status)
