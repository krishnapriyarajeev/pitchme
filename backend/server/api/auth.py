from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from server.deps import DbSession
from server.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from server.security import create_access_token
from server.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _response(user_id) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user_id), user_id=user_id)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: DbSession) -> AuthResponse:
    user = auth_service.register(
        db, email=body.email, password=body.password, display_name=body.display_name
    )
    return _response(user.id)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: DbSession) -> AuthResponse:
    user = auth_service.authenticate(db, email=body.email, password=body.password)
    return _response(user.id)


@router.post("/token", response_model=AuthResponse, include_in_schema=False)
def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> AuthResponse:
    """Form login used by the Authorize button in /docs (username = email)."""
    user = auth_service.authenticate(db, email=form.username, password=form.password)
    return _response(user.id)
