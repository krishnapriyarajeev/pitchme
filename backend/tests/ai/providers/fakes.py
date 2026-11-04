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


class FakeGenAI:
    """Mimics `client.models.generate_content(...)` of google-genai."""

    def __init__(self, text: str | None = "ok", error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._text = text
        self._error = error
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(text=self._text)


class FakeTranscriptions:
    """Mimics `client.audio.transcriptions.create(...)` of the Groq SDK."""

    def __init__(self, data: dict[str, Any] | None = None, error: Exception | None = None):
        self.calls: list[dict[str, Any]] = []
        self._data = data or {}
        self._error = error
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> Any:
        kwargs["file"] = (kwargs["file"][0], kwargs["file"][1].read())
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(model_dump=lambda: self._data)
