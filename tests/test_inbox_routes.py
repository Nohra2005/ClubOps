"""The OSA inbox routes (T-47): list waiting forwards for free, read one into Review on a person's click.
Synthetic mail and a scripted model only."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clubops.api.app import ApiConfig, create_app
from clubops.api.security import MemberStore
from clubops.contracts.common import Role
from clubops.inbox.capture import PendingInbox
from clubops.inbox.guards import InboxLedger
from clubops.inbox_intake import InboxNotes, intake
from tests.factories import CLUB, NOW
from tests.test_learning import BLK, HEADERS, LESSON, Provider

FORWARDER = "tp01@mail.aub.edu"
OTHER_CLUB = "chess-club"


OSA = "osa.staff@example.org"


def _mail(club: str, subject: str, original: str = OSA, body: str = "") -> bytes:
    """An Outlook-style forward (synthetic): marker line, then the original header lines."""
    return (
        f"From: {FORWARDER}\nTo: clubops.agent+{club}@gmail.com\nSubject: FW: {subject}\n"
        "Date: Tue, 10 Nov 2026 13:00:00 +0200\nContent-Type: text/plain\n\n"
        "________________________________\n"
        f"From: OSA Staff <{original}>\nSent: Tuesday, November 10, 2026 1:00 PM\n"
        "To: Student A <a@example.org>; Student B <b@example.org>\nCc: Second Staff <s@example.org>\n"
        f"Subject: {subject}\n\n{body or BLK}\n"
    ).encode()


class Gateway:
    def __init__(self, mails: dict[str, bytes]) -> None:
        self.mails = mails

    def list_ids(self) -> list[str]:
        return list(self.mails)

    def get_raw(self, message_id: str) -> bytes:
        return self.mails[message_id]


def _fetch(data: Path, mails: dict[str, bytes]) -> dict[str, int]:
    return intake(
        Gateway(mails),
        PendingInbox(data / "inbox.db"),
        notes=InboxNotes(data / "inbox-notes.db"),
        ledger=InboxLedger(data / "inbox-ledger.db"),
        cabinet={CLUB: {FORWARDER}, OTHER_CLUB: {FORWARDER}},
        osa_senders={OSA},
        received_at=datetime(2026, 11, 10, tzinfo=UTC),
    )


def _queue(data: Path, message_id: str, club: str, subject: str = "Sponsor note") -> None:
    assert _fetch(data, {message_id: _mail(club, subject)})["queued"] == 1


@pytest.fixture
def app(tmp_path: Path) -> Iterator[tuple[TestClient, Provider, Path]]:
    people = MemberStore(tmp_path)
    people.add(CLUB, "Test President", FORWARDER, Role.PRESIDENT)
    people.add(CLUB, "Test Adviser", "ta03@mail.aub.edu", Role.ADVISER)
    people.close()
    provider = Provider()
    config = ApiConfig(data_dir=tmp_path, session_secret="t", dev_login=True, cookie_secure=False)  # noqa: S106
    with TestClient(create_app(config, clock=lambda: NOW, model_client=lambda: provider.client(tmp_path))) as c:
        c.post("/api/auth/dev", json={"email": FORWARDER}, headers=HEADERS)
        yield c, provider, tmp_path


def test_listing_is_free_and_shows_metadata_only(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    _queue(data, "m1", CLUB)
    [row] = c.get("/api/inbox").json()
    assert row["id"] == "m1" and row["subject"] == "FW: Sponsor note" and row["forwarded_by"] == FORWARDER
    assert "Cafe B" not in str(row)  # no body before a person chooses to read it
    assert provider.prompts == []  # no model call


def test_another_clubs_mail_is_invisible_and_cannot_be_read(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    _queue(data, "x1", OTHER_CLUB)
    assert c.get("/api/inbox").json() == []
    assert c.post("/api/inbox/x1/capture", headers=HEADERS).status_code == 404
    assert provider.prompts == []


def test_reading_sends_proposals_to_review_and_leaves_the_queue(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    _queue(data, "m1", CLUB)
    provider.answers.append({"facts": [LESSON]})
    response = c.post("/api/inbox/m1/capture", headers=HEADERS)
    assert response.status_code == 200 and len(response.json()["proposals"]) == 1
    assert len(provider.prompts) == 1
    assert c.get("/api/inbox").json() == []
    assert any(card["id"] in response.json()["proposals"] for card in c.get("/api/review").json())
    assert c.post("/api/inbox/m1/capture", headers=HEADERS).status_code == 404  # never paid for twice


def test_a_failed_read_stays_waiting(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    _queue(data, "m1", CLUB)
    provider.answers.append("this is not JSON")
    assert c.post("/api/inbox/m1/capture", headers=HEADERS).status_code >= 400
    assert [row["id"] for row in c.get("/api/inbox").json()] == ["m1"]


def test_the_adviser_cannot_see_or_read_the_inbox(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    _queue(data, "m1", CLUB)
    c.post("/api/auth/dev", json={"email": "ta03@mail.aub.edu"}, headers=HEADERS)
    assert c.get("/api/inbox").status_code == 403
    assert c.post("/api/inbox/m1/capture", headers=HEADERS).status_code == 403
    assert provider.prompts == []


def test_non_osa_mail_is_skipped_with_a_reason_and_never_read(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    counts = _fetch(data, {"n1": _mail(CLUB, "Party", original="friend@example.org")})
    assert counts == {"queued": 0, "skipped": 1, "not_for_a_club": 0}
    assert c.get("/api/inbox").json() == []
    [row] = c.get("/api/inbox/skipped").json()
    assert row["id"] == "n1" and row["why"] == "ClubOps only reads e-mails forwarded from OSA staff"
    assert c.post("/api/inbox/n1/capture", headers=HEADERS).status_code == 404
    assert provider.prompts == []


def test_mail_queued_without_the_checks_is_never_paid_for(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    from clubops.inbox.capture import capture_email  # the old J-10 path, without J-22's checks

    request = capture_email(_mail(CLUB, "Old path"), "o1", {CLUB: {FORWARDER}}, datetime(2026, 11, 10, tzinfo=UTC))
    assert request is not None and PendingInbox(data / "inbox.db").enqueue("o1", request)
    assert c.post("/api/inbox/o1/capture", headers=HEADERS).status_code == 409
    assert provider.prompts == []


def test_the_same_osa_mail_for_two_clubs_is_paid_for_once(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    _queue(data, "m1", CLUB)
    _queue(data, "m2", OTHER_CLUB)  # same OSA e-mail forwarded to a second club
    provider.answers.append({"facts": [LESSON]})
    assert c.post("/api/inbox/m1/capture", headers=HEADERS).status_code == 200
    assert _fetch(data, {"m3": _mail(CLUB, "Sponsor note")})["skipped"] == 1  # already read
    assert len(provider.prompts) == 1


def test_a_read_in_progress_blocks_a_second_paid_read(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    _queue(data, "m1", CLUB)
    fingerprint = InboxNotes(data / "inbox-notes.db").fingerprint("m1", CLUB)
    assert fingerprint is not None and InboxLedger(data / "inbox-ledger.db").claim_read(fingerprint)
    assert c.post("/api/inbox/m1/capture", headers=HEADERS).status_code == 409
    assert provider.prompts == []
