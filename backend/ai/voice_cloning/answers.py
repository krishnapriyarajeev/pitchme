"""Rewrite each answer the content judge flagged into a stronger one.

Input is `ContentReport.needs_work`: each finding already holds the buyer's
question, the user's answer, why it was flagged and any playbook evidence.
A rewrite is expected to differ a lot from a dodged answer, so there is no
wording-similarity check. Facts are checked instead: every number in the
rewrite must appear in the answer, the question or the evidence. A
rewrite that brings in a new number is kept but marked unverified, and is
not played back by default.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ai.core.llm import LLMClient, LLMError
from ai.core.types import Finding
from ai.providers import get_llm_client

from .numbers import unsupported_numbers
from .prompts.answers import RESPONSE_SCHEMA, SYSTEM_PROMPT, AnswersResponse, build_prompt


@dataclass(frozen=True)
class AnswerCorrection:
    exchange_id: str
    category: str
    customer_quote: str
    original_answer: str
    stronger_response: str
    citation: str
    change_summary: str
    # Numbers in the rewrite found in none of the sources.
    unsupported_numbers: tuple[str, ...] = ()
    # Where the original answer (or the question) was said, for the debrief.
    t_start_ms: int | None = None

    @property
    def verified(self) -> bool:
        return not self.unsupported_numbers


def _exchange(finding: Finding, index: int) -> dict[str, str]:
    d = finding.details
    return {
        "id": f"ex-{index}",
        "customer_quote": d.get("customer_quote", ""),
        "agent_quote": d.get("agent_quote", ""),
        "category": finding.category,
        "reasoning": finding.summary,
        "reference_evidence": d.get("reference_evidence", ""),
    }


def correct_answers(
    needs_work: Sequence[Finding], llm: LLMClient | None = None
) -> tuple[AnswerCorrection, ...]:
    """One correction per flagged exchange the model answered, in input
    order. An id the model invents is ignored; an exchange it skips is
    missing from the result. Raises LLMError on a malformed reply."""
    if not needs_work:
        return ()
    exchanges = [_exchange(f, i) for i, f in enumerate(needs_work)]
    raw = (llm or get_llm_client()).complete_json(
        build_prompt(exchanges), schema=RESPONSE_SCHEMA, system=SYSTEM_PROMPT
    )
    try:
        reply = AnswersResponse.model_validate(raw)
    except ValueError as exc:
        raise LLMError(f"Answer rewrite reply did not match the expected shape: {exc}") from exc

    by_id = {item.exchange_id: item for item in reply.responses if item.stronger_response.strip()}
    corrections = []
    for finding, exchange in zip(needs_work, exchanges, strict=True):
        item = by_id.get(exchange["id"])
        if item is None:
            continue
        text = item.stronger_response.strip()
        corrections.append(
            AnswerCorrection(
                exchange_id=exchange["id"],
                category=finding.category,
                customer_quote=exchange["customer_quote"],
                original_answer=exchange["agent_quote"],
                stronger_response=text,
                citation=item.citation.strip(),
                change_summary=item.change_summary.strip(),
                unsupported_numbers=unsupported_numbers(
                    text,
                    exchange["agent_quote"],
                    exchange["customer_quote"],
                    exchange["reference_evidence"],
                ),
                t_start_ms=finding.note.t_start_ms if finding.note else None,
            )
        )
    return tuple(corrections)
