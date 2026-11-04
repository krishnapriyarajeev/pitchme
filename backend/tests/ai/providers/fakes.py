"""Stand-ins for provider SDK clients, so tests never touch the network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class FakeChat:
    """Mimics `client.chat.completions.create(...)` of OpenAI-style SDKs."""

    def __init__(self, reply: str | None = "ok", error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._reply = reply
        self._error = error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        message = SimpleNamespace(content=self._reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])
