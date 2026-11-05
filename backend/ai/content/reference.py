"""Reference material (the user's playbook) as plain text in sections.

Supported: .pdf, .pptx, .docx, .txt, .md, .vtt, .srt

Each file is split where the format has a natural unit (a page, a slide, a
heading, a caption), so a finding can say where in the playbook its
evidence came from ("Slide 7"). The judge reads the whole document at once;
sections only label it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# About 15k tokens. Past this the rest of the document is cut, so one huge
# deck cannot crowd the transcript out of the prompt.
MAX_REFERENCE_CHARS = 60_000


class ReferenceExtractionError(RuntimeError):
    """The file type is not supported, or the file has no usable text."""


@dataclass(frozen=True)
class ReferenceSection:
    index: int
    # Where this came from, shown to the user: "Page 3", "Slide 7", "Pricing".
    label: str
    text: str


@dataclass(frozen=True)
class ReferenceDocument:
    sections: tuple[ReferenceSection, ...]
    name: str = ""

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"[{s.label}]\n{s.text}" for s in self.sections)

    @property
    def truncated(self) -> bool:
        return len(self.full_text) > MAX_REFERENCE_CHARS

    @property
    def text(self) -> str:
        """Every section with its label, cut to MAX_REFERENCE_CHARS."""
        full = self.full_text
        if len(full) <= MAX_REFERENCE_CHARS:
            return full
        return full[:MAX_REFERENCE_CHARS].rsplit("\n", 1)[0] + "\n[... reference cut for length]"


def _sections(labelled: list[tuple[str, str]]) -> tuple[ReferenceSection, ...]:
    kept = [(label, text.strip()) for label, text in labelled if text and text.strip()]
    return tuple(ReferenceSection(i, label, text) for i, (label, text) in enumerate(kept))


def _pdf(path: Path) -> tuple[ReferenceSection, ...]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return _sections(
        [(f"Page {i + 1}", page.extract_text() or "") for i, page in enumerate(reader.pages)]
    )


def _table_rows(table) -> list[str]:
    return [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]


def _pptx(path: Path) -> tuple[ReferenceSection, ...]:
    """Slide text, tables and speaker notes. Notes often hold the talk
    track, which is exactly what the judge should check against."""
    from pptx import Presentation

    labelled = []
    for i, slide in enumerate(Presentation(str(path)).slides):
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                parts.append(shape.text_frame.text)
            elif getattr(shape, "has_table", False) and shape.has_table:
                parts.extend(_table_rows(shape.table))
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                parts.append(f"Notes: {notes}")
        labelled.append((f"Slide {i + 1}", "\n".join(parts)))
    return _sections(labelled)


def _docx(path: Path) -> tuple[ReferenceSection, ...]:
    """One section per heading with everything under it, tables included.
    A document with no headings is one section."""
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))
    labelled: list[tuple[str, str]] = []
    label, lines = "Document", []
    # Walk the body in order so tables stay under their heading.
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            para = Paragraph(child, doc)
            text = para.text.strip()
            style = (para.style.name if para.style is not None else "").lower()
            if text and style.startswith(("heading", "title")):
                labelled.append((label, "\n".join(lines)))
                label, lines = text, []
            elif text:
                lines.append(text)
        elif tag == "tbl":
            lines.extend(_table_rows(Table(child, doc)))
    labelled.append((label, "\n".join(lines)))
    return _sections(labelled)


def _plain(path: Path) -> tuple[ReferenceSection, ...]:
    return _sections([("Notes", path.read_text(encoding="utf-8", errors="replace"))])


_CUE_TIME = re.compile(
    r"((?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})"
)
_TAG = re.compile(r"<[^>]+>")


def parse_captions(raw: str) -> tuple[ReferenceSection, ...]:
    """WebVTT or SRT cues, labelled with their start time. Voice and style
    tags (<v Sam>, <i>) are removed, and NOTE and STYLE blocks skipped."""
    labelled = []
    for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n")):
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        for i, line in enumerate(lines):
            match = _CUE_TIME.search(line)
            if match:
                text = " ".join(_TAG.sub("", t) for t in lines[i + 1 :]).strip()
                labelled.append((match.group(1).replace(",", "."), text))
                break
    return _sections(labelled)


def _captions(path: Path) -> tuple[ReferenceSection, ...]:
    return parse_captions(path.read_text(encoding="utf-8", errors="replace"))


EXTRACTORS = {
    ".pdf": _pdf,
    ".pptx": _pptx,
    ".docx": _docx,
    ".txt": _plain,
    ".md": _plain,
    ".vtt": _captions,
    ".srt": _captions,
}


def extract_reference(path: str | Path) -> ReferenceDocument:
    """Read a reference file. Raises ReferenceExtractionError for an
    unsupported type or a file with no text (for example a deck of images)."""
    source = Path(path)
    extractor = EXTRACTORS.get(source.suffix.lower())
    if extractor is None:
        raise ReferenceExtractionError(
            f"Unsupported reference file type {source.suffix or '(none)'}. "
            f"Use one of: {', '.join(sorted(EXTRACTORS))}"
        )
    if not source.is_file():
        raise FileNotFoundError(f"Reference file not found: {source}")
    try:
        sections = extractor(source)
    except ImportError as exc:  # pragma: no cover - depends on the install
        raise ReferenceExtractionError(
            "Reading this file type needs the content extra. Run: uv sync --extra content"
        ) from exc
    except ReferenceExtractionError:
        raise
    except Exception as exc:
        raise ReferenceExtractionError(f"Could not read {source.name}: {exc}") from exc
    if not sections:
        raise ReferenceExtractionError(
            f"No text found in {source.name}. It may be empty or made only of images."
        )
    return ReferenceDocument(sections=sections, name=source.name)
