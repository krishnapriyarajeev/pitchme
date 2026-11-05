"""Real calls to the hosted providers. They spend quota, so they only run
when asked for:

    make test-live

Each test skips when its key is not in .env. Set LIVE_AUDIO_SAMPLE to a
short recording of speech to include the transcription check.
"""

import os

import pytest

from ai.config import AISettings
from ai.providers import make_llm_client, make_transcribe_client

pytestmark = pytest.mark.live

SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "integer"}},
    "required": ["answer"],
}


def _settings(provider: str) -> AISettings:
    settings = AISettings(llm_provider=provider, transcribe_provider="groq")
    key = settings.groq_api_key if provider == "groq" else settings.gemini_api_key
    if not key.get_secret_value():
        pytest.skip(f"{provider.upper()}_API_KEY is not set")
    return settings


@pytest.mark.parametrize("provider", ["groq", "gemini"])
def test_llm_complete(provider):
    reply = make_llm_client(_settings(provider)).complete("Reply with exactly the word: pong")
    assert "pong" in reply.lower()


@pytest.mark.parametrize("provider", ["groq", "gemini"])
def test_llm_complete_json(provider):
    reply = make_llm_client(_settings(provider)).complete_json(
        "What is 2 + 3? Put the number in `answer`.", schema=SCHEMA
    )
    assert reply["answer"] == 5


def test_groq_whisper():
    sample = os.environ.get("LIVE_AUDIO_SAMPLE")
    if not sample:
        pytest.skip("LIVE_AUDIO_SAMPLE is not set")
    transcript = make_transcribe_client(_settings("groq")).transcribe(sample)
    assert not transcript.is_empty
    assert transcript.words
    assert all(word.start_ms <= word.end_ms for word in transcript.words)
    assert transcript.segments[0].confidence is not None


@pytest.mark.parametrize("provider", ["groq", "gemini"])
def test_filler_detection(provider):
    from ai.core.transcript import Segment, Transcript, Word
    from ai.speech.fluency import count_fillers

    text = "So, um, our tool, like, cuts churn. Um, you know, customers like it."
    words = tuple(Word(w, i * 400, i * 400 + 300) for i, w in enumerate(text.split()))
    transcript = Transcript(segments=(Segment(text, 0, words[-1].end_ms, words),))
    fillers, summary = count_fillers(transcript, make_llm_client(_settings(provider)))
    found = {f.word: f.count for f in fillers}
    assert found.get("um") == 2
    # "like" in "customers like it" is a real verb, so at most one counts.
    assert found.get("like", 0) <= 1
    assert summary


@pytest.mark.parametrize("provider", ["groq", "gemini"])
def test_content_judge(provider):
    from ai.content import Line, score_content

    lines = (
        Line("customer", "How much is the team plan?", 0, 2000),
        Line("agent", "The team plan is forty dollars per seat each month.", 2500, 5000),
        Line("customer", "Is your product SOC 2 certified?", 6000, 8000),
        Line("agent", "Great question. Let me tell you about our new dashboard.", 8500, 11000),
    )
    report = score_content(lines, llm=make_llm_client(_settings(provider)))
    categories = {f.details["customer_quote"].lower(): f.category for f in report.findings}
    soc = next(c for q, c in categories.items() if "soc" in q)
    price = next(c for q, c in categories.items() if "plan" in q)
    assert soc in ("dodged", "weak")
    assert price in ("handled", "weak")
    assert 0 <= report.score <= 100
