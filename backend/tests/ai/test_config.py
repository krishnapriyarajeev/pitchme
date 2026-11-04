from ai.config import AISettings


def test_defaults(monkeypatch):
    for name in ("LLM_PROVIDER", "TRANSCRIBE_PROVIDER", "GROQ_MODEL"):
        monkeypatch.delenv(name, raising=False)
    settings = AISettings(_env_file=None)
    assert settings.llm_provider == "groq"
    assert settings.transcribe_provider == "groq"
    assert settings.groq_model == "openai/gpt-oss-20b"
    assert settings.groq_api_key.get_secret_value() == ""


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "key-from-env")
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "small")
    settings = AISettings(_env_file=None)
    assert settings.llm_provider == "gemini"
    assert settings.gemini_api_key.get_secret_value() == "key-from-env"
    assert settings.whisper_model_size == "small"


def test_secrets_are_hidden_in_repr(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "do-not-print")
    assert "do-not-print" not in repr(AISettings(_env_file=None))
