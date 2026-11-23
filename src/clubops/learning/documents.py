"""Big documents: read the text of a PDF and cut it into pieces the learner can take (F-242, D-135).

Plain code, no model. The learner reads at most ``MAX_SOURCE_CHARS`` of one source and silently dropped the
rest, so a long guide lost its end. Here a long text is cut at paragraph breaks, never in the middle of a
sentence, and every piece becomes its own source. Pictures are not read: a PDF with images says so.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PyPdfError

PIECE_CHARS = 5500  # a little under the learner's limit, so a piece is never cut again
MAX_PIECES = 12
MAX_PAGES = 60


class DocumentError(ValueError):
    """The file can't be used; the message is safe to show."""


@dataclass(frozen=True)
class PdfText:
    text: str
    pages: int
    images: int  # pictures found; their content is not read


def read_pdf(data: bytes) -> PdfText:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise DocumentError("This PDF is password protected.")
        pages = reader.pages[:MAX_PAGES]
        texts = [(page.extract_text() or "").strip() for page in pages]
        images = sum(len(page.images) for page in pages)
    except DocumentError:
        raise
    except (PyPdfError, ValueError, KeyError, OSError):
        raise DocumentError("This PDF can't be opened.") from None
    return PdfText("\n\n".join(t for t in texts if t), len(pages), images)


def split_text(text: str, limit: int = PIECE_CHARS) -> list[str]:
    """Pieces of at most ``limit`` characters, cut at blank lines, then line ends, then spaces."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        for part in _fit(paragraph, limit):
            if current and len(current) + len(part) + 2 > limit:
                pieces.append(current)
                current = part
            else:
                current = f"{current}\n\n{part}" if current else part
    if current:
        pieces.append(current)
    return pieces


def _fit(paragraph: str, limit: int) -> list[str]:
    if len(paragraph) <= limit:
        return [paragraph]
    out: list[str] = []
    rest = paragraph
    while len(rest) > limit:
        cut = next(
            (
                c
                for c in (rest.rfind("\n", 0, limit), rest.rfind(". ", 0, limit) + 1, rest.rfind(" ", 0, limit))
                if c > 0
            ),
            limit,
        )
        out.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        out.append(rest)
    return out
