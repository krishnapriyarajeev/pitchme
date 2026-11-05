"""Prompt and reply shape for the light rewrite of a solo talk.

Unlike the answer rewrite, this is a close edit: drop fillers, fix what the
content judge flagged, and give each segment delivery cues, so the user
hears their own talk done well, not a different talk. The whole transcript
goes in one call, so a fix can depend on earlier wording.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..base import EMOTIONS

SYSTEM_PROMPT = f"""\
You lightly correct a spoken talk so it can be re-recorded in the \
speaker's own voice, guided by findings from three checks: content \
(inaccurate or unsupported claims), speech (fillers, pace, hesitation) and \
voice (monotone, rushed, tense).

The talk is split into numbered segments. For EVERY segment return:
- "segment_index": its number from the input
- "corrected_text": the segment with its findings fixed; exactly the \
original text when no finding applies
- "change_description": one short sentence on what changed, or ""
- "related_finding_ids": ids of the findings this segment addresses
- "emotion": one of {", ".join(EMOTIONS)}; livelier where a finding says the \
delivery was flat
- "speed": 1.0 is normal, lower is slower (0.6 to 1.5); slower where a \
finding says the speaker rushed
- "pause_after_ms": silence after the segment, 0 if none

Findings with "segment_index": -1 cover the whole recording (for example \
overall tension or pace). Never edit wording for them; apply them as the \
same emotion or speed change on every segment, and list their id on each.

Rules: remove fillers (um, uh, like, you know). Fix flagged claims by \
correcting the wording, never by adding facts, numbers or details that are \
not already in the talk. Keep the speaker's own words wherever no finding \
requires a change. Never merge or split segments."""


class ScriptSegment(BaseModel):
    segment_index: int
    corrected_text: str
    change_description: str = ""
    related_finding_ids: list[str] = []
    emotion: str = "neutral"
    speed: float = 1.0
    pause_after_ms: int = 0


class ScriptResponse(BaseModel):
    segments: list[ScriptSegment]


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment_index": {"type": "integer"},
                    "corrected_text": {"type": "string"},
                    "change_description": {"type": "string"},
                    "related_finding_ids": {"type": "array", "items": {"type": "string"}},
                    "emotion": {"type": "string", "enum": list(EMOTIONS)},
                    "speed": {"type": "number"},
                    "pause_after_ms": {"type": "integer"},
                },
                "required": [
                    "segment_index",
                    "corrected_text",
                    "change_description",
                    "related_finding_ids",
                    "emotion",
                    "speed",
                    "pause_after_ms",
                ],
            },
        }
    },
    "required": ["segments"],
}


def build_prompt(segments: list[str], findings: list[dict]) -> str:
    numbered = "\n".join(f"[{i}] {text}" for i, text in enumerate(segments))
    listed = "\n".join(
        f"- id={f['id']} segment_index={f['segment_index']} "
        f"{f['pipeline']}/{f['category']}: {f['summary']}"
        for f in findings
    )
    return f"TALK SEGMENTS:\n{numbered}\n\nFINDINGS:\n{listed or '(none)'}"
