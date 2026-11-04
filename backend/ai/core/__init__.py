"""Contracts shared by more than one pipeline: the LLM client, the transcript
and the finding shape. Concrete providers live in `ai/providers/`."""

from .llm import LLMClient, LLMError, parse_json_object
from .transcript import Segment, Transcript, Word
from .types import Finding, Severity, TimestampedNote

__all__ = [
    "Finding",
    "LLMClient",
    "LLMError",
    "Segment",
    "Severity",
    "TimestampedNote",
    "Transcript",
    "Word",
    "parse_json_object",
]
