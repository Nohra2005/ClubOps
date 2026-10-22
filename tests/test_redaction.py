"""Redaction hides phones, AUB IDs, e-mails and links, and leaves ordinary numbers alone.

All numbers, addresses and IDs here are made up.
"""

from __future__ import annotations

import pytest

from clubops.redaction import redact


@pytest.mark.parametrize(
    "phone",
    [
        "+961 3 123 456",
        "+961 70 123 456",
        "\u202a+961 71 234 567\u202c",  # how WhatsApp exports wrap numbers
        "76 123456",
        "70123456",
        "81 234567",
        "03 123 456",
        "3 123 456",
        "01 234 567",
        "70 12 34 56",
        "+33 6 12 34 56 78",
        "+1 (555) 010\u20110199",
        "+961-76-123-456",
    ],
)
def test_phone_numbers_are_hidden(phone: str) -> None:
    out = redact(f"Call {phone} to register")
    assert out.text == "Call [PHONE] to register"
    assert out.counts["phone"] == 1


def test_aub_id_email_and_link_are_hidden() -> None:
    out = redact("ID 202312345, mail abc12@mail.aub.edu, form https://forms.office.com/r/XyZ123?embed=1 ok")
    assert out.text == "ID [AUB_ID], mail [EMAIL], form [LINK forms.office.com] ok"
    assert out.kinds == ["aub_id", "email", "other_pii"]


def test_a_link_keeps_only_the_website_name() -> None:
    out = redact("Drive: https://mailaub-my.sharepoint.com/:x:/g/personal/abc12_mail_aub_edu/EYiw?e=t")
    assert out.text == "Drive: [LINK mailaub-my.sharepoint.com]"
    assert "abc12" not in out.text  # SharePoint links carry the AUB username


@pytest.mark.parametrize(
    "ordinary",
    [
        "Whish budget 1500-3000",
        "Event on 9/28/2026 at 17:00",
        "Fall 2025-2026 term",
        "Students $30 / $45 relay",
        "100,000 LL per lap",
        "CRN 5153",
        "10 km run, 750 m swim, 20 km bike",
        "Red Cross hotline 1760",
        "Meet at 5:30, leave at 5:35",
        "Laps 3, 5 and 7",
        "Room 410 and 407",
        "50-70 people expected",
    ],
)
def test_ordinary_numbers_are_left_alone(ordinary: str) -> None:
    out = redact(ordinary)
    assert out.text == ordinary
    assert not out.counts


def test_several_items_are_counted() -> None:
    out = redact("Ask 76 123456 or 81 234567, or write to a@b.com")
    assert out.counts["phone"] == 2
    assert out.counts["email"] == 1
    assert out.kinds == ["phone", "email"]


def test_names_are_kept() -> None:
    out = redact("Tala at OSA approved it")
    assert out.text == "Tala at OSA approved it"
