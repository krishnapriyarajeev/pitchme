"""Content pipeline: how well the user answered the buyer.

One LLM call reads the whole conversation, finds each question or
objection and judges the answer, against the user's playbook when there is
one.

    from ai.content import Line, extract_reference, score_content
    report = score_content(lines, extract_reference("playbook.pdf"))
"""

from .reference import (
    ReferenceDocument,
    ReferenceExtractionError,
    ReferenceSection,
    extract_reference,
)
from .report import ContentReport, Line, lines_from_turns, locate, score_content

__all__ = [
    "ContentReport",
    "Line",
    "ReferenceDocument",
    "ReferenceExtractionError",
    "ReferenceSection",
    "extract_reference",
    "lines_from_turns",
    "locate",
    "score_content",
]
