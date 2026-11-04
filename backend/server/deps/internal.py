"""Shared-key check for calls from our own workers (the LiveKit agent)."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, Header

from server.config import Settings, get_settings
from server.errors import Forbidden


def verify_internal_key(
    settings: Annotated[Settings, Depends(get_settings)],
    x_internal_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = settings.ai_callback_key.get_secret_value()
    # An unset key must never match an empty header.
    if not expected or not x_internal_key or not hmac.compare_digest(x_internal_key, expected):
        raise Forbidden("Invalid internal key.")


InternalCaller = Depends(verify_internal_key)
