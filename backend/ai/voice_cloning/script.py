"""Lightly rewrite a solo talk using every pipeline's findings.

1. Each finding is placed on the transcript segments its time range
   overlaps. A finding with no time (an overall voice measure) is global.
2. One LLM call rewrites every segment and gives it delivery cues.
3. Each rewrite is checked: it must stay close to the original wording and
   length, and bring in no new number. A segment that fails is spoken as
   originally said, so one bad edit cannot spoil the playback.
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from dataclasses import dataclass

from ai.core.llm import LLMClient, LLMError
from ai.core.transcript import Transcript
from ai.core.types import Finding
from ai.providers import get_llm_client

from .base import ProsodyParams
from .numbers import unsupported_numbers
from .prompts.script import RESPONSE_SCHEMA, SYSTEM_PROMPT, ScriptResponse, build_prompt

# A rewrite less similar than this to the original no longer sounds like
# what the speaker said.
MIN_WORDING_SIMILARITY = 0.5
# A rewrite this much shorter or longer changes the timing too much.
WORD_COUNT_RATIO = (0.5, 1.3)


@dataclass(frozen=True)
class AlignedFinding:
    id: str
    finding: Finding
    # Empty for a global finding.
    segment_indices: tuple[int, ...]


@dataclass(frozen=True)
class ScriptSegment:
    index: int
    original_text: str
    corrected_text: str
    change_description: str
    related_finding_ids: tuple[str, ...]
    prosody: ProsodyParams
    # Why the rewrite was rejected; empty when it was accepted or unchanged.
    rejected_because: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.corrected_text != self.original_text

    @property
    def text_to_speak(self) -> str:
        return self.original_text if self.rejected_because else self.corrected_text


def align_findings(
    findings: Sequence[Finding], transcript: Transcript
) -> tuple[AlignedFinding, ...]:
    aligned = []
    for i, finding in enumerate(findings):
        note = finding.note
        indices: tuple[int, ...] = ()
        if note is not None:
            start, end = note.t_start_ms, max(note.t_end_ms, note.t_start_ms + 1)
            indices = tuple(
                j
                for j, segment in enumerate(transcript.segments)
                if segment.start_ms < end and segment.end_ms > start
            )
        aligned.append(AlignedFinding(f"{finding.pipeline}-{i}", finding, indices))
    return tuple(aligned)


def check_rewrite(original: str, corrected: str) -> tuple[str, ...]:
    """Reasons to reject a rewrite; empty when it is acceptable."""
    if corrected == original:
        return ()
    reasons = []
    similarity = difflib.SequenceMatcher(None, original.lower(), corrected.lower()).ratio()
    if similarity < MIN_WORDING_SIMILARITY:
        reasons.append(f"wording similarity {similarity:.2f} is below {MIN_WORDING_SIMILARITY}")
    before, after = len(original.split()), len(corrected.split())
    low, high = WORD_COUNT_RATIO
    if before and not low <= after / before <= high:
        reasons.append(f"length changed from {before} to {after} words")
    if new := unsupported_numbers(corrected, original):
        reasons.append(f"adds numbers not in the original: {', '.join(new)}")
    return tuple(reasons)


def correct_script(
    transcript: Transcript, findings: Sequence[Finding], llm: LLMClient | None = None
) -> tuple[ScriptSegment, ...]:
    """One ScriptSegment per transcript segment, in order. A segment the
    model skipped comes back unchanged with neutral delivery."""
    if not transcript.segments:
        return ()
    aligned = align_findings(findings, transcript)
    payload = [
        {
            "id": a.id,
            "segment_index": a.segment_indices[0] if a.segment_indices else -1,
            "pipeline": a.finding.pipeline,
            "category": a.finding.category,
            "summary": a.finding.summary,
        }
        for a in aligned
    ]
    texts = [segment.text for segment in transcript.segments]
    raw = (llm or get_llm_client()).complete_json(
        build_prompt(texts, payload), schema=RESPONSE_SCHEMA, system=SYSTEM_PROMPT
    )
    try:
        reply = ScriptResponse.model_validate(raw)
    except ValueError as exc:
        raise LLMError(f"Script rewrite reply did not match the expected shape: {exc}") from exc

    known_ids = {a.id for a in aligned}
    by_index = {item.segment_index: item for item in reply.segments}
    out = []
    for i, original in enumerate(texts):
        item = by_index.get(i)
        if item is None:
            out.append(ScriptSegment(i, original, original, "", (), ProsodyParams()))
            continue
        corrected = item.corrected_text.strip() or original
        out.append(
            ScriptSegment(
                index=i,
                original_text=original,
                corrected_text=corrected,
                change_description=item.change_description.strip(),
                related_finding_ids=tuple(f for f in item.related_finding_ids if f in known_ids),
                prosody=ProsodyParams(item.emotion, item.speed, item.pause_after_ms),
                rejected_because=check_rewrite(original, corrected),
            )
        )
    return tuple(out)
