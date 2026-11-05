"""Content report: one LLM call judging how the user answered the buyer.

Input is the conversation as lines with a role, so it works the same for a
LiveKit call (which knows who said what) and for one mixed recording that
went through diarization (see `lines_from_turns`).

The model never sees timings, so each quote is found again in the
conversation: to the exact words when the line has word timings, otherwise
to the closest line. A dodged question has no answer to point at, so its
finding points at the question.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from ai.core.llm import LLMClient, LLMError
from ai.core.types import Finding, Severity, TimestampedNote
from ai.providers import get_llm_client

from .prompts.content_judge import (
    ACCURACY_CATEGORIES,
    RESPONSE_SCHEMA,
    SYSTEM_PROMPT,
    ContentJudgeResponse,
    ExchangeCategory,
    ExchangeItem,
    build_prompt,
)
from .reference import ReferenceDocument

PIPELINE = "content"
Role = Literal["agent", "customer"]

SEVERITY = {
    ExchangeCategory.DODGED: Severity.HIGH,
    ExchangeCategory.INACCURATE: Severity.HIGH,
    ExchangeCategory.UNSUPPORTED: Severity.MEDIUM,
    ExchangeCategory.WEAK: Severity.MEDIUM,
    ExchangeCategory.HANDLED: Severity.INFO,
}

# Below this similarity a paraphrased quote is not matched to a line; an
# honest "unknown" time beats pointing at the wrong moment.
QUOTE_MATCH_THRESHOLD = 0.6


class TimedWord(Protocol):
    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class Line:
    role: Role
    text: str
    start_ms: int
    end_ms: int
    words: tuple[TimedWord, ...] = field(default=(), compare=False)


@dataclass(frozen=True)
class ContentReport:
    # None when there was nothing to judge.
    score: int | None
    summary: str
    findings: tuple[Finding, ...]
    used_reference: bool = False

    @property
    def needs_work(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity.rank >= Severity.MEDIUM.rank)


class _Turn(Protocol):
    speaker: str | None
    words: Sequence[TimedWord]
    start_ms: int
    end_ms: int
    text: str


def lines_from_turns(turns: Sequence[_Turn], agent_speaker: str) -> tuple[Line, ...]:
    """Diarized turns (ai.diarize.align.Turn) as conversation lines. A turn
    with no known speaker is given to the user."""
    return tuple(
        Line(
            role="agent" if turn.speaker in (None, agent_speaker) else "customer",
            text=turn.text,
            start_ms=turn.start_ms,
            end_ms=turn.end_ms,
            words=tuple(turn.words),
        )
        for turn in turns
    )


def conversation_text(lines: Sequence[Line]) -> str:
    return "\n".join(f"{line.role.upper()}: {line.text}" for line in lines)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.lower())


def _exact_span(quote: list[str], line: Line) -> tuple[int, int] | None:
    """Start and end time of the words that spell out `quote` in `line`."""
    tokens: list[tuple[str, TimedWord]] = [
        (token, word) for word in line.words for token in _tokens(word.text)
    ]
    size = len(quote)
    for i in range(len(tokens) - size + 1):
        if [t for t, _ in tokens[i : i + size]] == quote:
            return tokens[i][1].start_ms, tokens[i + size - 1][1].end_ms
    return None


def locate(quote: str, lines: Sequence[Line]) -> TimestampedNote | None:
    """Where in `lines` the quote was said, or None if it cannot be found."""
    wanted = _tokens(quote)
    if not wanted:
        return None
    joined = " ".join(wanted)
    best: tuple[float, Line] | None = None
    for line in lines:
        have = " ".join(_tokens(line.text))
        if joined in have:
            span = _exact_span(wanted, line) if line.words else None
            start, end = span or (line.start_ms, line.end_ms)
            return TimestampedNote(start, end, quote)
        ratio = difflib.SequenceMatcher(None, joined, have).ratio()
        if best is None or ratio > best[0]:
            best = (ratio, line)
    if best and best[0] >= QUOTE_MATCH_THRESHOLD:
        return TimestampedNote(best[1].start_ms, best[1].end_ms, quote)
    return None


def _finding(item: ExchangeItem, lines: Sequence[Line]) -> Finding:
    agent_lines = [line for line in lines if line.role == "agent"]
    customer_lines = [line for line in lines if line.role == "customer"]
    answer = locate(item.agent_quote, agent_lines)
    question = locate(item.customer_quote, customer_lines)
    return Finding(
        pipeline=PIPELINE,
        category=item.category.value,
        severity=SEVERITY[item.category],
        summary=item.reasoning.strip(),
        note=answer or question,
        details={
            "customer_quote": item.customer_quote,
            "agent_quote": item.agent_quote,
            "handled_well": item.category is ExchangeCategory.HANDLED,
            "reference_evidence": item.reference_evidence,
            "points_at": "answer" if answer else "question" if question else None,
            "question_found": question is not None,
        },
    )


def score_content(
    lines: Sequence[Line],
    reference: ReferenceDocument | None = None,
    llm: LLMClient | None = None,
) -> ContentReport:
    """Judge every buyer question in the conversation, worst first.

    Raises LLMError when the reply does not match `ContentJudgeResponse`.
    """
    used_reference = reference is not None
    if not any(line.role == "customer" for line in lines):
        return ContentReport(
            score=None,
            summary="The buyer asked nothing, so there were no answers to judge.",
            findings=(
                Finding(
                    PIPELINE,
                    "no_questions",
                    Severity.INFO,
                    "No buyer questions were found in this conversation.",
                ),
            ),
            used_reference=used_reference,
        )

    prompt = build_prompt(conversation_text(lines), reference.text if reference else None)
    raw = (llm or get_llm_client()).complete_json(
        prompt, schema=RESPONSE_SCHEMA, system=SYSTEM_PROMPT
    )
    try:
        reply = ContentJudgeResponse.model_validate(raw)
    except ValueError as exc:
        raise LLMError(f"Content judge reply did not match the expected shape: {exc}") from exc

    findings = []
    for item in reply.exchanges:
        if not used_reference and item.category in ACCURACY_CATEGORIES:
            # Nothing to be inaccurate against; the prompt forbids this, but
            # a small model can still slip.
            item = item.model_copy(update={"category": ExchangeCategory.WEAK})
        findings.append(_finding(item, lines))
    findings.sort(key=lambda f: (-f.severity.rank, f.note.t_start_ms if f.note else 1 << 62))

    return ContentReport(
        score=reply.score,
        summary=reply.summary.strip(),
        findings=tuple(findings),
        used_reference=used_reference,
    )
