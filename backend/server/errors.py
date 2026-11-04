"""Domain errors and how they map to HTTP responses.

Services raise these; one handler turns them into JSON, so routes stay thin
and services stay free of HTTP details.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.__doc__ or self.code)
        self.message = str(self)


class NotFound(DomainError):
    """Not found."""

    status_code = 404
    code = "not_found"


class Conflict(DomainError):
    """Conflicts with the current state."""

    status_code = 409
    code = "conflict"


class Forbidden(DomainError):
    """Not allowed."""

    status_code = 403
    code = "forbidden"


class Unauthorized(DomainError):
    """Not signed in."""

    status_code = 401
    code = "unauthorized"


class EmailTaken(Conflict):
    """An account with this email already exists."""

    code = "email_taken"


class InvalidCredentials(Unauthorized):
    """Email or password is wrong."""

    code = "invalid_credentials"


class InvalidUpload(DomainError):
    """The uploaded file is missing or not acceptable."""

    status_code = 422
    code = "invalid_upload"


class StorageUnavailable(DomainError):
    """File storage is not reachable right now."""

    status_code = 503
    code = "storage_unavailable"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
            headers=headers,
        )
