from __future__ import annotations

from fastapi import APIRouter

from server.deps import CurrentUser, DbSession
from server.deps.storage import StorageDep
from server.schemas.profile import ProfileResponse, ProfileUpdateRequest
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
