"""Prompt and reply shape for filler word detection.

There is no fixed word list. A list of "um", "uh" and "like" misses the
speaker's own habit ("so basically", "right?") and counts "like" in "I like
this plan". The model reads the whole transcript and decides what was used
as a filler in this talk.

`FillersResponse` is the real check on the reply. Groq does not enforce the
schema on its side, so fluency validates every reply against this model.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FillerItem(BaseModel):
    word: str
    count: int = Field(ge=0)


class FillersResponse(BaseModel):
    fillers: list[FillerItem]
    # One sentence for the debrief, written by the model.
    summary: str


SYSTEM_PROMPT = """\
You find filler words and phrases in a spoken transcript. A filler is a word
or short phrase the speaker uses as a verbal crutch, with no meaning of its
own, for example "um", "uh", "like", "you know", "sort of", "basically",
"right?".

Count a word only where it is used as a filler. The same word can carry real
meaning elsewhere in the transcript; do not count that use. "like" in "I like
this plan" is not a filler. "like" in "it's, like, really good" is.

Write each filler exactly as it appears in the transcript, in lower case.

Return:
- "fillers": one entry per distinct filler, with how many times it was used
  as a filler in the whole transcript. Return an empty list if there were none.
- "summary": one short sentence on the speaker's filler use, for example which
  word they lean on and how often. If there were none, say so plainly."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "fillers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "count": {"type": "integer"},
                },
                "required": ["word", "count"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["fillers", "summary"],
}


def build_prompt(transcript_text: str) -> str:
    return f"TRANSCRIPT:\n{transcript_text}"
