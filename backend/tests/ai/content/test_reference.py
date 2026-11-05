import pytest

from ai.content import reference
from ai.content.reference import (
    ReferenceDocument,
    ReferenceExtractionError,
    ReferenceSection,
    extract_reference,
    parse_captions,
)

from . import files


def _labels(doc):
    return [(s.label, s.text) for s in doc.sections]


def test_pdf_pages(tmp_path):
    doc = extract_reference(files.pdf(tmp_path / "deck.pdf", ["Cuts churn 20%", "", "Team $40"]))
    assert _labels(doc) == [("Page 1", "Cuts churn 20%"), ("Page 3", "Team $40")]
    assert doc.name == "deck.pdf"


def test_pptx_reads_text_tables_and_notes(tmp_path):
    doc = extract_reference(files.pptx(tmp_path / "deck.pptx"))
    assert [s.label for s in doc.sections] == ["Slide 1", "Slide 2"]
    assert doc.sections[0].text == (
        "Why Acme\nCuts churn by 20%\nNotes: Mention the Globex case study"
    )
    assert "Plan | Price\nTeam | $40" in doc.sections[1].text


def test_docx_splits_on_headings_and_keeps_tables_in_place(tmp_path):
    doc = extract_reference(files.docx(tmp_path / "playbook.docx"))
    assert _labels(doc) == [
        ("Document", "Acme playbook"),
        ("Pricing", "Team plan is $40 per seat.\nDiscount | 10% yearly"),
        ("Objections", "If asked about security, cite SOC 2."),
    ]


def test_docx_without_headings_is_one_section(tmp_path):
    doc = extract_reference(files.docx(tmp_path / "flat.docx", headings=False))
    assert [s.label for s in doc.sections] == ["Document"]


@pytest.mark.parametrize("suffix", [".txt", ".md"])
def test_plain_text(tmp_path, suffix):
    path = tmp_path / f"notes{suffix}"
    path.write_text("  Lead with ROI.\n")
    assert _labels(extract_reference(path)) == [("Notes", "Lead with ROI.")]


VTT = """WEBVTT

NOTE this block is a comment
00:00:09.000 --> 00:00:10.000

1
00:00:01.000 --> 00:00:03.500
<v Sam>We cut churn</v>
<i>by twenty percent</i>

00:00:04.000 --> 00:00:05.000
Next question
"""

SRT = """1
00:00:01,000 --> 00:00:02,000
Hello there

2
00:00:02,500 --> 00:00:04,000
Our price is $40
"""


def test_vtt_drops_tags_and_notes():
    assert _labels(ReferenceDocument(parse_captions(VTT))) == [
        ("00:00:01.000", "We cut churn by twenty percent"),
        ("00:00:04.000", "Next question"),
    ]


def test_srt(tmp_path):
    path = tmp_path / "talk.srt"
    path.write_text(SRT.replace("\n", "\r\n"))
    assert _labels(extract_reference(path)) == [
        ("00:00:01.000", "Hello there"),
        ("00:00:02.500", "Our price is $40"),
    ]


def test_text_joins_labelled_sections():
    doc = ReferenceDocument(
        (ReferenceSection(0, "Slide 1", "A"), ReferenceSection(1, "Slide 2", "B"))
    )
    assert doc.text == "[Slide 1]\nA\n\n[Slide 2]\nB"
    assert not doc.truncated


def test_long_reference_is_cut(monkeypatch):
    monkeypatch.setattr(reference, "MAX_REFERENCE_CHARS", 40)
    lines = "\n".join(f"line {i}" for i in range(20))
    doc = ReferenceDocument((ReferenceSection(0, "Notes", lines),))
    assert doc.truncated
    assert doc.text.endswith("[... reference cut for length]")
    assert len(doc.text.split("\n[...")[0]) <= 40


def test_unsupported_type(tmp_path):
    with pytest.raises(ReferenceExtractionError, match=r"Unsupported reference file type \.xlsx"):
        extract_reference(tmp_path / "sheet.xlsx")


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_reference(tmp_path / "gone.pdf")


def test_empty_file(tmp_path):
    (tmp_path / "empty.txt").write_text("   ")
    with pytest.raises(ReferenceExtractionError, match=r"No text found in empty\.txt"):
        extract_reference(tmp_path / "empty.txt")


def test_corrupt_file(tmp_path):
    (tmp_path / "broken.pptx").write_bytes(b"not a zip")
    with pytest.raises(ReferenceExtractionError, match=r"Could not read broken\.pptx"):
        extract_reference(tmp_path / "broken.pptx")
