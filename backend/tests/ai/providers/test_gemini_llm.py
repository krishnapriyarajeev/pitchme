import pytest

from ai.core import LLMError
from ai.providers.gemini.llm import GeminiClient

from .fakes import FakeGenAI


def test_missing_key():
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        GeminiClient(api_key=None)


def test_builds_sdk_client_from_key():
    assert GeminiClient(api_key="test-key-not-used", model="m").model == "m"


def test_retries_busy_responses_but_not_quota_errors():
    client = GeminiClient(api_key="test-key-not-used")
    retry = client._client._api_client._http_options.retry_options
    assert retry.attempts == 4
    assert retry.http_status_codes == [500, 503]


def test_complete_passes_system_instruction():
    fake = FakeGenAI(text="pong")
    client = GeminiClient(client=fake, model="m", max_output_tokens=99)
    assert client.complete("ping", system="Be brief") == "pong"
    call = fake.calls[0]
    assert call["model"] == "m"
    assert call["contents"] == "ping"
    assert call["config"].system_instruction == "Be brief"
    assert call["config"].max_output_tokens == 99


def test_complete_empty_reply():
    with pytest.raises(LLMError, match="empty"):
        GeminiClient(client=FakeGenAI(text=None)).complete("ping")


def test_complete_wraps_sdk_errors():
    fake = FakeGenAI(error=RuntimeError("429 RESOURCE_EXHAUSTED"))
    with pytest.raises(LLMError, match="Gemini call failed: 429"):
        GeminiClient(client=fake).complete("ping")


def test_complete_json_enforces_schema():
    fake = FakeGenAI(text='{"score": 4}')
    schema = {"type": "object", "properties": {"score": {"type": "integer"}}}
    assert GeminiClient(client=fake).complete_json("Rate it", schema=schema) == {"score": 4}
    config = fake.calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == schema


def test_complete_json_bad_reply():
    with pytest.raises(LLMError, match="valid JSON"):
        GeminiClient(client=FakeGenAI(text="nope")).complete_json("x", schema={})
