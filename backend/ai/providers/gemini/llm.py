"""Gemini as an LLMClient.

Gemini enforces the JSON Schema server-side, so `complete_json` replies
always match the requested shape. The free tier allows only a few requests
per day, so Groq is the default and Gemini is the alternative.
"""

from __future__ import annotations

from typing import Any

from ai.core.llm import LLMClient, LLMError, parse_json_object

DEFAULT_MODEL = "gemini-3.8-flash"
# The SDK does not retry by default; 500 and 503 ("high demand") pass
# quickly. 429 is not retried: on the free tier it is usually the daily
# quota, and every retry spends more of it.
RETRY_ATTEMPTS = 4
RETRY_STATUS_CODES = (500, 503)
KEY_HELP = "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey"


class GeminiClient(LLMClient):
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
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(
                        attempts=RETRY_ATTEMPTS, http_status_codes=list(RETRY_STATUS_CODES)
                    )
                ),
            )
        self._client = client
        self.model = model
        self._max_output_tokens = max_output_tokens

    def _generate(self, prompt: str, **config: Any) -> str | None:
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=self._max_output_tokens, **config
                ),
            )
        except Exception as exc:
            raise LLMError(f"Gemini call failed: {exc}") from exc
        return response.text

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        text = self._generate(prompt, system_instruction=system)
        if not text or not text.strip():
            raise LLMError("Gemini returned an empty response")
        return text

    def complete_json(
        self, prompt: str, *, schema: dict[str, Any], system: str | None = None
    ) -> dict[str, Any]:
        text = self._generate(
            prompt,
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
        )
        return parse_json_object(text, "Gemini")
