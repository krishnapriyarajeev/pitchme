"""The buyer persona on a real Groq model, in a text-only agent session.
No speech, so no Deepgram key is needed. Runs with make test-live."""

import pytest

from ai.config import AISettings
from ai.rehearsal.deal import Deal

pytestmark = pytest.mark.live
pytest.importorskip("livekit.plugins.groq", reason="needs the rehearsal extra")

DEAL = Deal(
    "Jo Bennett",
    "Saber Industries",
    deal_stage="negotiation",
    buyer_composure="direct",
    competitors="Staples",
    audience_type="procurement",
    product="Payroll software for small teams",
)


async def test_buyer_stays_in_character_and_pushes_on_price():
    from livekit.agents import AgentSession
    from livekit.plugins import groq

    from ai.rehearsal.agent import BuyerAgent

    settings = AISettings()
    if not settings.groq_api_key.get_secret_value():
        pytest.skip("GROQ_API_KEY is not set")
    llm = groq.LLM(model=settings.groq_model, api_key=settings.groq_api_key.get_secret_value())
    async with AgentSession(llm=llm) as session:
        await session.start(BuyerAgent(DEAL))
        result = await session.run(
            user_input="Hi Jo, thanks for making time. So, are we good to sign at the list price?"
        )
        reply = result.expect.next_event().is_message(role="assistant").event().item.text_content
    print(reply)
    lowered = reply.lower()
    assert reply.strip()
    assert "*" not in reply and "\n-" not in reply  # spoken, not formatted
    assert "assistant" not in lowered and "language model" not in lowered
    assert len(reply.split()) < 90  # a turn, not a speech
    assert any(w in lowered for w in ("price", "discount", "cost", "budget", "terms", "staples"))
