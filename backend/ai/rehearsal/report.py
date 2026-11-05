"""Tell the API how a call went: once when the seller joins, once at the end.

The worker must finish its cleanup even when the API is down, so these
calls retry a few times and then log the failure instead of raising.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import httpx

from .transcript import CallTurn

log = logging.getLogger(__name__)

EndedBy = Literal["seller_left", "time_limit", "no_show", "error"]


@dataclass(frozen=True)
class CallReport:
    turns: tuple[CallTurn, ...]
    ended_by: EndedBy
    ended_at: datetime
    # None when the seller never joined.
    started_at: datetime | None = None
    error: str | None = None

    def to_json(self) -> dict[str, Any]:
        duration = (
            round((self.ended_at - self.started_at).total_seconds(), 2) if self.started_at else None
        )
        return {
            "transcript": [t.to_dict() for t in self.turns],
            "ended_by": self.ended_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat(),
            "duration_seconds": duration,
            "error": self.error,
        }


class ResultsClient:
    def __init__(
        self,
        base_url: str,
        key: str,
        *,
        http: httpx.AsyncClient | None = None,
        attempts: int = 3,
        backoff_s: float = 1.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._http = http or httpx.AsyncClient(timeout=15)
        self._base = base_url.rstrip("/")
        self._headers = {"X-Internal-Key": key}
        self._attempts = attempts
        self._backoff_s = backoff_s
        self._sleep = sleep

    async def __aenter__(self) -> ResultsClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._http.aclose()

    async def started(self, session_id: str, at: datetime) -> bool:
        return await self._post(
            f"/internal/sessions/{session_id}/started", {"started_at": at.isoformat()}
        )

    async def finished(self, session_id: str, report: CallReport) -> bool:
        return await self._post(f"/internal/sessions/{session_id}/results", report.to_json())

    async def _post(self, path: str, body: dict[str, Any]) -> bool:
        """True once the API accepted it. Network errors and 5xx are retried;
        a 4xx (bad key, unknown or finished session) will not change, so it
        is logged once."""
        for attempt in range(1, self._attempts + 1):
            try:
                response = await self._http.post(
                    self._base + path, json=body, headers=self._headers
                )
            except httpx.HTTPError as exc:
                problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.is_success:
                    return True
                problem = f"HTTP {response.status_code}: {response.text[:200]}"
                if response.status_code < 500:
                    log.error("API refused %s: %s", path, problem)
                    return False
            if attempt < self._attempts:
                await self._sleep(self._backoff_s * 2 ** (attempt - 1))
        log.error(
            "Could not reach the API for %s after %d tries: %s", path, self._attempts, problem
        )
        return False
