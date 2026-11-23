"""Big documents: PDF text, cutting long text into pieces, pictures flagged (F-242, D-135)."""

from __future__ import annotations

import pytest

from clubops.learning.documents import PIECE_CHARS, DocumentError, read_pdf, split_text


def make_pdf(pages: list[str], with_image: bool = False) -> bytes:
    """A tiny valid PDF with one line of text per page (and, optionally, one picture on page one)."""
    objs: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    kids = []
    font = 3
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    image = 4
    objs.append(
        b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceGray /BitsPerComponent 8 "
        b"/Length 1 >>\nstream\n\x00\nendstream"
    )
    for i, text in enumerate(pages):
        page_no = len(objs) + 1
        kids.append(f"{page_no} 0 R")
        xobj = f"/XObject << /Im1 {image} 0 R >>" if with_image and i == 0 else ""
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Contents {page_no + 1} 0 R "
            f"/Resources << /Font << /F1 {font} 0 R >> {xobj} >> >>".encode()
        )
        body = f"BT /F1 12 Tf 20 700 Td ({text}) Tj ET"
        if with_image and i == 0:
            body += " q 10 0 0 10 20 600 cm /Im1 Do Q"
        objs.append(f"<< /Length {len(body)} >>\nstream\n{body}\nendstream".encode())
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()
    out = b"%PDF-1.4\n"
    offsets = []
    for n, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def test_pdf_text_is_read_page_by_page() -> None:
    pdf = read_pdf(make_pdf(["Step one: open the portal", "Step two: sign in"]))
    assert pdf.pages == 2 and pdf.images == 0
    assert "Step one: open the portal" in pdf.text and "Step two: sign in" in pdf.text


def test_pictures_in_a_pdf_are_counted_not_read() -> None:
    pdf = read_pdf(make_pdf(["Click Submit"], with_image=True))
    assert pdf.images == 1
    assert "Click Submit" in pdf.text


def test_a_file_that_is_not_a_pdf_is_refused_with_a_plain_message() -> None:
    with pytest.raises(DocumentError, match="can't be opened"):
        read_pdf(b"%PDF-1.4 nothing here")


def test_long_text_is_cut_at_paragraphs_and_nothing_is_lost() -> None:
    paragraphs = [f"Paragraph {n}. " + "word " * 200 for n in range(30)]
    pieces = split_text("\n\n".join(paragraphs))
    assert len(pieces) > 1
    assert all(len(p) <= PIECE_CHARS for p in pieces)
    assert "".join(pieces).replace("\n", "").replace(" ", "") == "".join(paragraphs).replace(" ", "")


def test_one_giant_paragraph_is_cut_at_sentence_or_space_not_mid_word() -> None:
    text = "Sentence number one. " * 1000
    pieces = split_text(text)
    assert all(len(p) <= PIECE_CHARS for p in pieces)
    assert all(p.endswith(".") for p in pieces)


def test_short_text_stays_one_piece() -> None:
    assert split_text("Short note.\n\nSecond line.") == ["Short note.\n\nSecond line."]
