"""Prompt and reply shape for rewriting weak answers.

This is not a light edit. A dodged or weak answer is replaced by a better
one, which may be longer or make a different argument. The rewrite is
played back in the user's own voice, so it must sound like them, and it
may only use facts from their answer, the buyer's question or the playbook.
"""

from __future__ import annotations

from pydantic import BaseModel

SYSTEM_PROMPT = """\
You rewrite a sales rep's answer to a buyer's question or objection, for \
every exchange that was flagged as dodged, inaccurate, unsupported or weak. \
The rewrite will be played back in the rep's own cloned voice.

For EVERY exchange, return:
- "exchange_id": copied exactly from the input
- "stronger_response": an answer that really addresses the buyer. Use only \
facts from the ORIGINAL ANSWER, the BUYER's words or the REFERENCE \
MATERIAL for that exchange. Never invent a number, feature, customer or \
claim. When the original was inaccurate or unsupported, ground the \
rewrite in the reference material's own figures and wording. With no \
reference material, improve directness, clarity and confidence only.
- "citation": the exact reference text the rewrite relies on, or ""
- "change_summary": one short sentence on why this answer is stronger

Keep the rep's own register and tone, and keep it to what someone would \
say aloud on a call: no lists, no headings, at most about 80 words."""


class AnswerItem(BaseModel):
    exchange_id: str
    stronger_response: str
    citation: str = ""
    change_summary: str = ""


class AnswersResponse(BaseModel):
    responses: list[AnswerItem]


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "responses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "exchange_id": {"type": "string"},
                    "stronger_response": {"type": "string"},
                    "citation": {"type": "string"},
                    "change_summary": {"type": "string"},
                },
                "required": ["exchange_id", "stronger_response", "citation", "change_summary"],
            },
        }
    },
    "required": ["responses"],
}


def build_prompt(exchanges: list[dict[str, str]]) -> str:
    blocks = [
        f"[{e['id']}]\n"
        f"BUYER: {e['customer_quote']}\n"
        f"ORIGINAL ANSWER: {e['agent_quote'] or '(no answer)'}\n"
        f"WHY IT WAS FLAGGED ({e['category']}): {e['reasoning']}\n"
        f"REFERENCE MATERIAL: {e['reference_evidence'] or '(none)'}"
        for e in exchanges
    ]
    return "EXCHANGES TO IMPROVE:\n\n" + "\n\n".join(blocks)
