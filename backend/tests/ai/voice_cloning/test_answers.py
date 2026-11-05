import pytest

from ai.core.llm import LLMError
from ai.core.types import Finding, Severity, TimestampedNote
from ai.voice_cloning.answers import correct_answers
from ai.voice_cloning.numbers import numbers_in, unsupported_numbers
from ai.voice_cloning.prompts.answers import SYSTEM_PROMPT
from tests.ai.speech.helpers import FakeLLM


def flagged(category, question, answer, evidence="", at=None):
    return Finding(
        "content",
        category,
        Severity.HIGH,
        f"You {category} it.",
        note=TimestampedNote(at, at + 1000, answer) if at is not None else None,
        details={
            "customer_quote": question,
            "agent_quote": answer,
            "reference_evidence": evidence,
        },
    )


NEEDS_WORK = (
    flagged("dodged", "Do you have SOC 2?", "", "We are SOC 2 Type II audited yearly.", at=12_000),
    flagged(
        "inaccurate", "How much per seat?", "About thirty dollars.", "Team plan: $40 per seat."
    ),
)


def reply(*items):
    return {
        "responses": [
            {"exchange_id": i, "stronger_response": t, "citation": c, "change_summary": "Better."}
            for i, t, c in items
        ]
    }


def test_rewrites_are_matched_to_their_exchange():
    llm = FakeLLM(
        reply(
            ("ex-1", "It's forty dollars a seat on the team plan.", "Team plan: $40 per seat."),
            ("ex-0", "Yes, we are SOC 2 Type II audited every year.", "SOC 2 Type II"),
            ("ex-9", "Invented exchange.", ""),
        )
    )
    soc, price = correct_answers(NEEDS_WORK, llm)
    assert (soc.exchange_id, soc.category, soc.t_start_ms) == ("ex-0", "dodged", 12_000)
    assert soc.customer_quote == "Do you have SOC 2?"
    assert soc.verified
    assert price.original_answer == "About thirty dollars."
    assert price.citation == "Team plan: $40 per seat."
    assert price.verified  # "forty" matches the $40 in the evidence
    assert price.t_start_ms is None


def test_prompt_carries_each_exchange():
    llm = FakeLLM(reply())
    correct_answers(NEEDS_WORK, llm)
    prompt = llm.prompts[0]
    assert "[ex-0]\nBUYER: Do you have SOC 2?\nORIGINAL ANSWER: (no answer)" in prompt
    assert "WHY IT WAS FLAGGED (inaccurate): You inaccurate it." in prompt
    assert "REFERENCE MATERIAL: Team plan: $40 per seat." in prompt
    assert "Never invent a number" in SYSTEM_PROMPT


def test_a_new_number_is_unverified():
    llm = FakeLLM(reply(("ex-1", "It's $40 a seat, and 25% off for 3 years.", "")))
    (price,) = correct_answers(NEEDS_WORK, llm)
    assert price.unsupported_numbers == ("3", "25")
    assert not price.verified


def test_skipped_and_empty_rewrites_are_dropped():
    llm = FakeLLM(reply(("ex-0", "  ", "")))
    assert correct_answers(NEEDS_WORK, llm) == ()


def test_nothing_to_fix_skips_the_model():
    llm = FakeLLM(reply())
    assert correct_answers((), llm) == ()
    assert llm.prompts == []


def test_malformed_reply():
    with pytest.raises(LLMError, match="did not match"):
        correct_answers(NEEDS_WORK, FakeLLM({"answers": []}))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("$40 per seat, 1,200 seats, 2.5x faster, 99.9%", {"40", "1200", "2.5", "99.9"}),
        ("forty dollars", {"40"}),
        ("twenty five percent", {"25"}),
        ("two hundred and fifty users", {"250"}),
        ("three thousand two hundred", {"3200"}),
        ("one million", {"1000000"}),
        ("no figures here", set()),
    ],
)
def test_numbers_in(text, expected):
    assert numbers_in(text) == expected


def test_unsupported_numbers():
    assert unsupported_numbers("We save 20% in 2 weeks", "twenty percent", "") == ("2",)
    assert unsupported_numbers("no numbers") == ()
