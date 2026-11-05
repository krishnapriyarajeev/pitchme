"""Prompt and reply shape for the content judge's one LLM call.

The model reads the whole conversation, labelled AGENT (the user, a sales
rep in practice) and CUSTOMER (the buyer), finds each question or objection
and judges the answer. With reference material it also checks accuracy;
without, it judges each answer on its own merits. Only the prompt text
changes between the two.

The model pairs questions with answers itself. A reply is not always the
next line: the rep may ask a clarifying question first, or answer two
objections at once.

`ContentJudgeResponse` is the real check on the reply. The schema below is
kept flat by hand because Gemini's schema support has no $ref, and Groq only
reads it as prompt text, where a flat shape is easier to follow.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, field_validator

SYSTEM_PROMPT = """\
You review a sales-practice conversation between a sales rep (AGENT, the \
person you coach) and a buyer (CUSTOMER). Each line says who spoke.

Find every customer question or objection and judge how well the answer \
handled it: against the rep's reference material (product facts, pricing, \
a battle card) when it is given, or on the answer's own merits when it is \
not.

Speak to the rep as "you" in "summary" and "reasoning": friendly and \
constructive. Write "You did not quite answer..." and never "The agent \
failed to...".

Return:
- "score": 0 to 100 for the whole conversation (100: every question \
handled well; 0: every question dodged or answered badly).
- "summary": one short paragraph of coaching on the whole conversation.
- "exchanges": one entry per customer question or objection, in order:
  - "customer_quote": the customer's exact words
  - "agent_quote": the rep's exact answer, or "" if they never answered it
  - "handled_well": true if the answer really addressed the question
  - "category": one of
      "dodged"      - not addressed at all
      "inaccurate"  - conflicts with the reference material (only when \
reference material is given)
      "unsupported" - a claim the reference material does not back (only \
when reference material is given)
      "weak"        - addressed, but vague, incomplete or unsure
      "handled"     - answered well (use when handled_well is true)
  - "reasoning": one sentence of coaching on why
  - "reference_evidence": the exact reference text the judgement rests on, \
or "" when there is none

Quote the transcript exactly. Do not invent questions, and do not count \
small talk or greetings. Report well-handled questions too, with \
"handled_well": true and "category": "handled"."""


class ExchangeCategory(enum.StrEnum):
    DODGED = "dodged"
    INACCURATE = "inaccurate"
    UNSUPPORTED = "unsupported"
    WEAK = "weak"
    HANDLED = "handled"


# Only meaningful when there is reference material to check against.
ACCURACY_CATEGORIES = (ExchangeCategory.INACCURATE, ExchangeCategory.UNSUPPORTED)


class ExchangeItem(BaseModel):
    customer_quote: str
    agent_quote: str = ""
    handled_well: bool
    category: ExchangeCategory
    reasoning: str
    reference_evidence: str = ""


class ContentJudgeResponse(BaseModel):
    score: int
    summary: str
    exchanges: list[ExchangeItem]

    @field_validator("score")
    @classmethod
    def _clamp(cls, value: int) -> int:
        return max(0, min(100, value))


_EXCHANGE = {
    "type": "object",
    "properties": {
        "customer_quote": {"type": "string"},
        "agent_quote": {"type": "string"},
        "handled_well": {"type": "boolean"},
        "category": {"type": "string", "enum": [c.value for c in ExchangeCategory]},
        "reasoning": {"type": "string"},
        "reference_evidence": {"type": "string"},
    },
    "required": [
        "customer_quote",
        "agent_quote",
        "handled_well",
        "category",
        "reasoning",
        "reference_evidence",
    ],
}

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "summary": {"type": "string"},
        "exchanges": {"type": "array", "items": _EXCHANGE},
    },
    "required": ["score", "summary", "exchanges"],
}


def build_prompt(conversation: str, reference_text: str | None) -> str:
    if reference_text is None:
        return f"TRANSCRIPT:\n{conversation}\n\nNO REFERENCE MATERIAL PROVIDED."
    return f"TRANSCRIPT:\n{conversation}\n\nREFERENCE MATERIAL:\n{reference_text}"
