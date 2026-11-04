"""Groq chat completions as an LLMClient.

The free tier allows far more requests per day than Gemini's, so this is the
default for development. Groq's JSON mode guarantees valid JSON but does not
enforce a schema, so `complete_json` puts the schema in the prompt.
"""

from __future__ import annotations

import json
from typing import Any

from ai.core.llm import LLMClient, LLMError, parse_json_object

DEFAULT_MODEL = "openai/gpt-oss-20b"
KEY_HELP = "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys"


class GroqClient(LLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        *,
        max_output_tokens: int = 4096,
        client: Any = None,
    ) -> None:
        if client is None:
            if not api_key:
                raise LLMError(KEY_HELP)
            from groq import Groq

            client = Groq(api_key=api_key)
        self._client = client
        self.model = model
        self._max_output_tokens = max_output_tokens

    @staticmethod
    def _messages(prompt: str, system: str | None) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        return messages

    def _create(self, **kwargs: Any) -> str | None:
        try:
            response = self._client.chat.completions.create(model=self.model, **kwargs)
        except Exception as exc:
            raise LLMError(f"Groq call failed: {exc}") from exc
        return response.choices[0].message.content

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        content = self._create(messages=self._messages(prompt, system))
        if not content or not content.strip():
            raise LLMError("Groq returned an empty response")
        return content

    def complete_json(
        self, prompt: str, *, schema: dict[str, Any], system: str | None = None
    ) -> dict[str, Any]:
        prompt = (
            f"{prompt}\n\nReply with one JSON object that matches this JSON Schema:\n"
            f"{json.dumps(schema)}"
        )
        content = self._create(
            messages=self._messages(prompt, system),
            response_format={"type": "json_object"},
            # The default cap cuts off long structured replies mid-object.
            max_completion_tokens=self._max_output_tokens,
        )
        return parse_json_object(content, "Groq")
