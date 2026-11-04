"""Who is calling: the signed-in user from the bearer token."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from server.db import User
from server.db.session import get_db
from server.errors import Unauthorized
from server.repositories import users
from server.security import TokenError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not token:
        raise Unauthorized()
    try:
        user_id = decode_access_token(token)
    except TokenError as exc:
        raise Unauthorized("Session expired or invalid; sign in again.") from exc
    user = users.get_by_id(db, user_id)
    if user is None:
        raise Unauthorized("Account no longer exists.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
