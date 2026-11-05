"""Build small playbook files in each supported format."""

from __future__ import annotations

from pathlib import Path


def pdf(path: Path, pages: list[str]) -> Path:
    """A minimal PDF with one line of Helvetica text per page."""
    objects: list[bytes] = []
    page_ids = [3 + 2 * i for i in range(len(pages))]
    font_id = 3 + 2 * len(pages)
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{i} 0 R" for i in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for i, text in enumerate(pages):
        content_id = page_ids[i] + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    path.write_bytes(bytes(out))
    return path


def pptx(path: Path) -> Path:
    from pptx import Presentation
    from pptx.util import Inches

    deck = Presentation()
    first = deck.slides.add_slide(deck.slide_layouts[1])
    first.shapes.title.text = "Why Acme"
    first.placeholders[1].text = "Cuts churn by 20%"
    first.notes_slide.notes_text_frame.text = "Mention the Globex case study"

    second = deck.slides.add_slide(deck.slide_layouts[5])
    second.shapes.title.text = "Pricing"
    table = second.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(4), Inches(1)).table
    for (r, c), text in {(0, 0): "Plan", (0, 1): "Price", (1, 0): "Team", (1, 1): "$40"}.items():
        table.cell(r, c).text = text

    deck.slides.add_slide(deck.slide_layouts[6])  # blank: no text at all
    deck.save(str(path))
    return path


def docx(path: Path, headings: bool = True) -> Path:
    from docx import Document

    doc = Document()
    doc.add_paragraph("Acme playbook")
    if headings:
        doc.add_heading("Pricing", level=1)
    doc.add_paragraph("Team plan is $40 per seat.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Discount"
    table.rows[0].cells[1].text = "10% yearly"
    if headings:
        doc.add_heading("Objections", level=1)
    doc.add_paragraph("If asked about security, cite SOC 2.")
    doc.save(str(path))
    return path
