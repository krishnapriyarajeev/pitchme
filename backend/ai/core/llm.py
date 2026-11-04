"""The LLM contract every pipeline codes against.

No provider is named here and no key is read here. Concrete clients live in
`ai/providers/`, and pipelines get one from `ai.providers.get_llm_client()`.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


class LLMError(RuntimeError):
    """An LLM call failed, or the reply could not be used."""


class LLMClient(ABC):
    """Text in, text or JSON out. Every pipeline uses only these two calls."""

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """The model's plain-text reply to one prompt."""

    @abstractmethod
    def complete_json(
        self, prompt: str, *, schema: dict[str, Any], system: str | None = None
    ) -> dict[str, Any]:
        """The model's reply parsed as a JSON object.

        `schema` is a JSON Schema for the expected object. A provider that
        cannot enforce it server-side passes it to the model as an instruction,
        so callers that need a hard guarantee validate the result themselves.
        """


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def parse_json_object(text: str | None, provider: str) -> dict[str, Any]:
    """Parse a model reply that should be one JSON object.

    Some models wrap JSON in a ```json fence even in JSON mode, so a single
    fence around the whole reply is removed first.
    """
    if not text or not text.strip():
        raise LLMError(f"{provider} returned an empty response")
    body = text.strip()
    if match := _FENCE.match(body):
        body = match.group(1)
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise LLMError(f"{provider} did not return valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError(f"{provider} returned JSON {type(data).__name__}, expected an object")
    return data
