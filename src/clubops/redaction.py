"""Hide personal data before any text reaches a model (D-09, D-36).

Replaced with placeholders: links (keeping only the website name), e-mail addresses, AUB ID
numbers, and phone numbers (Lebanese and international). Names are kept on purpose: who
decides what is part of the know-how (D-09).

Plain code, no model, so it is cheap, predictable and fully tested. It is deliberately careful
not to touch ordinary numbers: money ranges ("1500-3000"), dates, times, years, prices,
distances and the club's CRN stay as they are.

Known limit: AUB usernames written alone ("abc12") and spelled-out numbers are not caught.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["phone", "aub_id", "email", "other_pii"]

# WhatsApp exports wrap phone numbers in invisible direction marks; remove them first.
_INVISIBLE = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_SEP = "[ \u00a0\u202f\u2011.\\-]"

_URL = re.compile(r"https?://([^/\s?#]+)[^\s]*", re.IGNORECASE)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
# AUB ID numbers are 9 digits starting with the enrolment year, e.g. 2024xxxxx.
_AUB_ID = re.compile(r"(?<!\d)20\d{7}(?!\d)")
# International: a "+" then 8 to 15 digits with common separators and brackets.
_PHONE_INTL = re.compile("\\+\\d(?:[ \u00a0\u202f\u2011.\\-()]*\\d){7,14}")
# Lebanese without a country code: mobiles 03/3, 70, 71, 76, 78, 79, 81 or landlines 01-09,
# then exactly 6 more digits, possibly grouped ("76 123456", "3 123 456", "01 234 567").
_PHONE_LB = re.compile(rf"(?<![\d+/:])(?:0?(?:3|7[016-9]|81)|0[1-9])(?:{_SEP}?\d){{6}}(?![\d/:])")


@dataclass(frozen=True)
class Redacted:
    text: str
    counts: Counter[Kind] = field(default_factory=Counter)

    @property
    def kinds(self) -> list[Kind]:
        """Distinct kinds hidden, in a stable order (for ``KnowHowProposal.redactions``)."""
        order: list[Kind] = ["phone", "aub_id", "email", "other_pii"]
        return [k for k in order if self.counts[k]]


def redact(text: str, keep_office_contacts: bool = False) -> Redacted:
    """``keep_office_contacts``: leave links, e-mail addresses and phone numbers as written. Only for e-mails
    forwarded from verified OSA senders: office forms and office numbers are the know-how itself (F-241)."""
    counts: Counter[Kind] = Counter()

    def sub(pattern: re.Pattern[str], kind: Kind, replacement: str, value: str) -> str:
        def replace(match: re.Match[str]) -> str:
            counts[kind] += 1
            return match.expand(replacement)

        return pattern.sub(replace, value)

    out = _INVISIBLE.sub("", text)
    if not keep_office_contacts:
        out = sub(_URL, "other_pii", r"[LINK \1]", out)
        out = sub(_EMAIL, "email", "[EMAIL]", out)
    out = sub(_AUB_ID, "aub_id", "[AUB_ID]", out)
    if not keep_office_contacts:
        out = sub(_PHONE_INTL, "phone", "[PHONE]", out)
        out = sub(_PHONE_LB, "phone", "[PHONE]", out)
    return Redacted(text=out, counts=counts)
