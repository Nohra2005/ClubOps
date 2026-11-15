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
from clubops.inbox.capture import PendingInbox, capture_email
from tests.factories import CLUB, NOW
from tests.test_learning import BLK, HEADERS, LESSON, Provider

FORWARDER = "tp01@mail.aub.edu"
OTHER_CLUB = "chess-club"


def _mail(club: str, subject: str) -> bytes:
    return (
        f"From: {FORWARDER}\nTo: clubops.agent+{club}@gmail.com\nSubject: {subject}\n"
        "Date: Tue, 10 Nov 2026 13:00:00 +0200\nContent-Type: text/plain\n\n"
        f"{BLK}\n"
    ).encode()


def _queue(data: Path, message_id: str, club: str, subject: str = "FW: Sponsor note") -> None:
    request = capture_email(_mail(club, subject), message_id, {club: {FORWARDER}}, datetime(2026, 11, 10, tzinfo=UTC))
    assert request is not None
    assert PendingInbox(data / "inbox.db").enqueue(message_id, request)


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
