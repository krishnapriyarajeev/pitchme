"""The result shape every analysis pipeline reports in.

One shape lets the debrief show findings from any pipeline the same way.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class Severity(enum.StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        """0 for info up to 3 for high. Sort with `key=lambda f: -f.severity.rank`."""
        return list(Severity).index(self)


@dataclass(frozen=True)
class TimestampedNote:
    """The moment in the recording a finding points at, with what was said."""

    t_start_ms: int
    t_end_ms: int
    quote: str


@dataclass(frozen=True)
class Finding:
    """One thing a pipeline wants the user to see.

    `pipeline` is content, speech, voice or vision. `category` is defined by
    each pipeline (for example "filler" or "inaccurate").
    """

    pipeline: str
    category: str
    severity: Severity
    summary: str
    note: TimestampedNote | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict, for storing in the session's analysis data."""
        return {
            "pipeline": self.pipeline,
            "category": self.category,
            "severity": self.severity.value,
            "summary": self.summary,
            "note": None
            if self.note is None
            else {
                "t_start_ms": self.note.t_start_ms,
                "t_end_ms": self.note.t_end_ms,
                "quote": self.note.quote,
            },
            "details": self.details,
        }
