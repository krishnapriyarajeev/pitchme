"""Sign up and sign in."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.db import User
from server.errors import EmailTaken, InvalidCredentials
from server.repositories import users
from server.security import hash_password, verify_password

# Compared against when the email is unknown, so a wrong email takes as long
# as a wrong password and response time does not reveal which accounts exist.
_DUMMY_HASH = hash_password("timing-equalizer")


def register(db: Session, *, email: str, password: str, display_name: str | None) -> User:
    if users.get_by_email(db, email):
        raise EmailTaken()
    try:
        user = users.create(
            db, email=email, password_hash=hash_password(password), display_name=display_name
        )
        db.commit()
    except IntegrityError as exc:
        # Two sign-ups with the same email at the same moment.
        db.rollback()
        raise EmailTaken() from exc
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = users.get_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise InvalidCredentials()
    if not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return user
