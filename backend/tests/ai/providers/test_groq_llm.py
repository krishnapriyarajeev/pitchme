import pytest

from ai.core import LLMError
from ai.providers.groq.llm import GroqClient

from .fakes import FakeChat


def test_missing_key():
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        GroqClient(api_key="")


def test_builds_sdk_client_from_key():
    client = GroqClient(api_key="test-key-not-used", model="some-model")
    assert client.model == "some-model"


def test_complete_sends_system_and_user():
    fake = FakeChat(reply="pong")
    client = GroqClient(client=fake, model="m")
    assert client.complete("ping", system="Be brief") == "pong"
    call = fake.calls[0]
    assert call["model"] == "m"
    assert call["messages"] == [
        {"role": "system", "content": "Be brief"},
        {"role": "user", "content": "ping"},
    ]


def test_complete_without_system():
    fake = FakeChat()
    GroqClient(client=fake).complete("ping")
    assert fake.calls[0]["messages"] == [{"role": "user", "content": "ping"}]


def test_complete_empty_reply():
    with pytest.raises(LLMError, match="empty"):
        GroqClient(client=FakeChat(reply="")).complete("ping")


def test_complete_wraps_sdk_errors():
    fake = FakeChat(error=TimeoutError("read timed out"))
    with pytest.raises(LLMError, match="Groq call failed: read timed out"):
        GroqClient(client=fake).complete("ping")


def test_complete_json_uses_json_mode_and_schema_in_prompt():
    fake = FakeChat(reply='{"verdict": "accurate"}')
    schema = {"type": "object", "properties": {"verdict": {"type": "string"}}}
    client = GroqClient(client=fake, max_output_tokens=1234)

    assert client.complete_json("Judge this", schema=schema) == {"verdict": "accurate"}

    call = fake.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert call["max_completion_tokens"] == 1234
    prompt = call["messages"][-1]["content"]
    assert prompt.startswith("Judge this")
    assert '"verdict"' in prompt


def test_complete_json_bad_reply():
    with pytest.raises(LLMError, match="valid JSON"):
        GroqClient(client=FakeChat(reply="not json")).complete_json("x", schema={})
