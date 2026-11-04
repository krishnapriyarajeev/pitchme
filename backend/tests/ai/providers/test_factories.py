import sys

import pytest

from ai.config import AISettings
from ai.core import LLMError
from ai.providers import (
    get_llm_client,
    get_transcribe_client,
    make_llm_client,
    make_transcribe_client,
)
from ai.providers.gemini.llm import GeminiClient
from ai.providers.groq.llm import GroqClient
from ai.providers.groq.whisper import GroqWhisperClient
from ai.transcribe import TranscribeError


def _settings(**values) -> AISettings:
    return AISettings(_env_file=None, **values)


def test_llm_defaults_to_groq():
    client = make_llm_client(_settings(groq_api_key="k", groq_model="m"))
    assert isinstance(client, GroqClient)
    assert client.model == "m"


def test_llm_selects_gemini_case_insensitively():
    client = make_llm_client(_settings(llm_provider=" Gemini ", gemini_api_key="k"))
    assert isinstance(client, GeminiClient)


def test_llm_unknown_provider():
    with pytest.raises(LLMError, match=r"Unknown LLM_PROVIDER 'openai'\. Use one of: groq, gemini"):
        make_llm_client(_settings(llm_provider="openai"))


def test_llm_missing_key_names_the_variable():
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        make_llm_client(_settings(llm_provider="gemini"))


def test_transcribe_defaults_to_groq():
    client = make_transcribe_client(_settings(groq_api_key="k", whisper_model="w"))
    assert isinstance(client, GroqWhisperClient)
    assert client.model == "w"


def test_transcribe_local_without_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(TranscribeError, match="whisper-local"):
        make_transcribe_client(_settings(transcribe_provider="local"))


def test_transcribe_unknown_provider():
    with pytest.raises(TranscribeError, match="Unknown TRANSCRIBE_PROVIDER"):
        make_transcribe_client(_settings(transcribe_provider="deepgram"))


def test_get_clients_are_cached_from_env(monkeypatch):
    from ai.config import get_ai_settings

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("TRANSCRIBE_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-used")
    for cached in (get_ai_settings, get_llm_client, get_transcribe_client):
        cached.cache_clear()
    try:
        assert get_llm_client() is get_llm_client()
        assert isinstance(get_transcribe_client(), GroqWhisperClient)
    finally:
        for cached in (get_ai_settings, get_llm_client, get_transcribe_client):
            cached.cache_clear()
