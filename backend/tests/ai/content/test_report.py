import pytest

from ai.content import Line, lines_from_turns, locate, score_content
from ai.content.prompts.content_judge import (
    RESPONSE_SCHEMA,
    SYSTEM_PROMPT,
    ContentJudgeResponse,
    ExchangeCategory,
    build_prompt,
)
from ai.content.reference import ReferenceDocument, ReferenceSection
from ai.core.llm import LLMError
from ai.core.transcript import Segment, Transcript, Word
from ai.core.types import Severity
from ai.diarize.align import tag_speakers
from ai.diarize.base import DiarizedSegment as D
from tests.ai.speech.helpers import FakeLLM


def timed_line(role, text, start_ms):
    words = tuple(
        Word(w, start_ms + i * 500, start_ms + i * 500 + 400) for i, w in enumerate(text.split())
    )
    return Line(role, text, words[0].start_ms, words[-1].end_ms, words)


CALL = (
    timed_line("agent", "Hi, thanks for joining.", 0),
    timed_line("customer", "How much does the team plan cost?", 3000),
    timed_line("agent", "It is forty dollars per seat, billed monthly.", 7000),
    timed_line("customer", "Do you have SOC 2?", 12000),
    timed_line("agent", "Let me tell you about our roadmap instead.", 15000),
)

PLAYBOOK = ReferenceDocument((ReferenceSection(0, "Pricing", "Team plan: $40 per seat."),))


def exchange(category, customer, agent="", **extra):
    return {
        "customer_quote": customer,
        "agent_quote": agent,
        "handled_well": category == "handled",
        "category": category,
        "reasoning": f"You {category} it.",
        "reference_evidence": extra.get("evidence", ""),
    }


REPLY = {
    "score": 60,
    "summary": " You handled price well but skipped security. ",
    "exchanges": [
        exchange(
            "handled",
            "How much does the team plan cost?",
            "forty dollars per seat",
            evidence="Team plan: $40 per seat.",
        ),
        exchange("dodged", "Do you have SOC 2?", ""),
    ],
}


def test_findings_are_worst_first_with_times_from_the_words():
    llm = FakeLLM(REPLY)
    report = score_content(CALL, PLAYBOOK, llm)
    assert report.score == 60
    assert report.summary == "You handled price well but skipped security."
    assert report.used_reference
    dodged, handled = report.findings
    assert (dodged.category, dodged.severity) == ("dodged", Severity.HIGH)
    # No answer to point at, so it points at the question.
    assert dodged.details["points_at"] == "question"
    assert (dodged.note.t_start_ms, dodged.note.t_end_ms) == (12000, 14400)
    assert handled.severity is Severity.INFO
    assert handled.details["points_at"] == "answer"
    # "forty dollars per seat" is words 3-6 of the answer, which starts at 7 s.
    assert (handled.note.t_start_ms, handled.note.t_end_ms) == (8000, 9900)
    assert handled.details["reference_evidence"] == "Team plan: $40 per seat."
    assert report.needs_work == (dodged,)


def test_prompt_labels_roles_and_carries_the_reference():
    llm = FakeLLM(REPLY)
    score_content(CALL, PLAYBOOK, llm)
    prompt = llm.prompts[0]
    assert "CUSTOMER: How much does the team plan cost?" in prompt
    assert "AGENT: Hi, thanks for joining." in prompt
    assert "REFERENCE MATERIAL:\n[Pricing]\nTeam plan: $40 per seat." in prompt
    score_content(CALL, None, llm)
    assert llm.prompts[1].endswith("NO REFERENCE MATERIAL PROVIDED.")


def test_accuracy_categories_need_a_reference():
    reply = {
        "score": 50,
        "summary": "s",
        "exchanges": [exchange("inaccurate", "How much does the team plan cost?", "forty dollars")],
    }
    without = score_content(CALL, None, FakeLLM(reply))
    assert without.findings[0].category == "weak"
    with_ref = score_content(CALL, PLAYBOOK, FakeLLM(reply))
    assert with_ref.findings[0].category == "inaccurate"


def test_score_is_clamped():
    assert ContentJudgeResponse.model_validate({**REPLY, "score": 140}).score == 100
    assert ContentJudgeResponse.model_validate({**REPLY, "score": -5}).score == 0


@pytest.mark.parametrize(
    "reply",
    [
        {"summary": "no score", "exchanges": []},
        {"score": 50, "summary": "s", "exchanges": [{"customer_quote": "q"}]},
        {"score": 50, "summary": "s", "exchanges": [exchange("rude", "q")]},
    ],
)
def test_malformed_reply_raises(reply):
    with pytest.raises(LLMError, match="did not match"):
        score_content(CALL, None, FakeLLM(reply))


def test_no_buyer_lines_skips_the_model():
    llm = FakeLLM(REPLY)
    report = score_content(CALL[:1], None, llm)
    assert report.score is None
    assert [f.category for f in report.findings] == ["no_questions"]
    assert llm.prompts == []


def test_invented_question_is_flagged_not_placed():
    reply = {**REPLY, "exchanges": [exchange("weak", "What about the moon landing?", "")]}
    finding = score_content(CALL, None, FakeLLM(reply)).findings[0]
    assert finding.note is None
    assert finding.details["question_found"] is False


def test_locate_paraphrase_and_lines_without_words():
    plain = (Line("agent", "We integrate with Salesforce and HubSpot.", 1000, 4000),)
    exact = locate("Salesforce and HubSpot", plain)
    assert (exact.t_start_ms, exact.t_end_ms) == (1000, 4000)
    close = locate("we integrate with salesforce and hubspot!!", plain)
    assert close is not None
    assert locate("totally different words here", plain) is None
    assert locate("", plain) is None


def test_lines_from_diarized_turns():
    words = (Word("hello", 0, 400), Word("price?", 1000, 1500), Word("forty", 2000, 2400))
    transcript = Transcript(segments=(Segment("hello price? forty", 0, 2400, words),))
    segments = (D("S0", 0, 800), D("S1", 900, 1800), D("S0", 1900, 2500))
    lines = lines_from_turns(tag_speakers(transcript, segments).turns(), "S0")
    assert [(line.role, line.text) for line in lines] == [
        ("agent", "hello"),
        ("customer", "price?"),
        ("agent", "forty"),
    ]
    assert lines[1].words[0].start_ms == 1000


def test_prompt_and_schema_agree():
    assert set(RESPONSE_SCHEMA["required"]) == set(ContentJudgeResponse.model_fields)
    categories = RESPONSE_SCHEMA["properties"]["exchanges"]["items"]["properties"]["category"]
    assert categories["enum"] == [c.value for c in ExchangeCategory]
    for c in ExchangeCategory:
        assert f'"{c.value}"' in SYSTEM_PROMPT
    assert build_prompt("A: hi", "ref").endswith("REFERENCE MATERIAL:\nref")
