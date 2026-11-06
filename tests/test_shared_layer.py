"""Know-how about AUB is shared by every club (D-91); know-how about one club stays in that club.

A new club starts with what other clubs taught ClubOps about AUB, but only after a president approved it,
and a club can never pull a shared fact into its own layer (F-163). Synthetic data only."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clubops.api.app import ApiConfig, create_app
from clubops.api.security import MemberStore
from clubops.capabilities.runner import CapabilityError
from clubops.contracts.common import Role
from clubops.contracts.knowhow import ProposalOp, Scope, VerifyDecision, VerifyRequest
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore
from tests.factories import CLUB, NOW, actor, item, proposal, verified
from tests.test_learning import BLK, HEADERS, LESSON, Provider, capture

OTHER = "chess-club"
AUB_TEXT = "Room bookings in West Hall go through the OSA form at least five days ahead."
AUB_FACT = {
    "kind": "procedure",
    "title": "West Hall rooms are booked through OSA",
    "statement": "Book West Hall rooms through the OSA form at least five days ahead.",
    "quote": "go through the OSA form at least five days ahead",
    "source": 0,
    "about": "aub",
    "details": {"goal": "Book a West Hall room", "steps": [{"order": 1, "action": "Fill the OSA form"}]},
}


def test_a_fact_about_aub_is_proposed_for_every_club(tmp_path: Path) -> None:
    [p] = capture(KnowHowStore(), tmp_path, Provider({"facts": [AUB_FACT]}), AUB_TEXT).proposals
    assert p.candidate.scope is Scope.AUB and p.candidate.club_id is None
    assert "shared with every club" in p.rationale


def test_a_fact_about_the_club_stays_in_the_club(tmp_path: Path) -> None:
    [p] = capture(KnowHowStore(), tmp_path, Provider({"facts": [LESSON]}), BLK).proposals
    assert p.candidate.scope is Scope.CLUB and p.candidate.club_id == CLUB


# ----------------------------------------------------------- through the app


@pytest.fixture
def app(tmp_path: Path) -> Iterator[tuple[TestClient, Provider, Path]]:
    people = MemberStore(tmp_path)
    people.add(CLUB, "Test President", "tp01@mail.aub.edu", Role.PRESIDENT)
    people.add(CLUB, "Test Treasurer", "tt02@mail.aub.edu", Role.TREASURER)
    people.close()
    provider = Provider()
    config = ApiConfig(data_dir=tmp_path, session_secret="t", dev_login=True, cookie_secure=False)  # noqa: S106
    with TestClient(create_app(config, clock=lambda: NOW, model_client=lambda: provider.client(tmp_path))) as c:
        c.post("/api/auth/dev", json={"email": "tp01@mail.aub.edu"}, headers=HEADERS)
        yield c, provider, tmp_path


def teach(c: TestClient, provider: Provider, fact: dict[str, object], text: str) -> str:
    provider.answers.append({"facts": [fact]})
    review_id: str = c.post("/api/chat/teach", json={"text": text}, headers=HEADERS).json()["review_id"]
    return review_id


def titles_seen_by(data: Path, club: str) -> set[str]:
    store = KnowHowStore(open_club_store_backend(data, club))
    try:
        return {i.title for i in store.visible(club)}
    finally:
        store.close()


def test_an_approved_aub_fact_reaches_a_brand_new_club(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    rid = teach(c, provider, AUB_FACT, AUB_TEXT)
    assert c.get("/api/review").json()[0]["shared"] is True
    assert c.post(f"/api/review/{rid}", json={"decision": "approve"}, headers=HEADERS).status_code == 200
    assert AUB_FACT["title"] in titles_seen_by(data, OTHER)


def test_the_president_can_keep_a_shared_guess_in_the_club(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    rid = teach(c, provider, AUB_FACT, AUB_TEXT)
    c.post(f"/api/review/{rid}", json={"decision": "approve", "shared": False}, headers=HEADERS)
    assert AUB_FACT["title"] in titles_seen_by(data, CLUB)
    assert AUB_FACT["title"] not in titles_seen_by(data, OTHER)


def test_the_president_can_share_a_club_guess(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    rid = teach(c, provider, LESSON, BLK)
    c.post(f"/api/review/{rid}", json={"decision": "approve", "shared": True}, headers=HEADERS)
    assert LESSON["title"] in titles_seen_by(data, OTHER)


def test_only_a_president_shares_with_every_club(app: tuple[TestClient, Provider, Path]) -> None:
    c, provider, data = app
    rid = teach(c, provider, AUB_FACT, AUB_TEXT)
    c.post("/api/auth/dev", json={"email": "tt02@mail.aub.edu"}, headers=HEADERS)
    assert c.post(f"/api/review/{rid}", json={"decision": "approve"}, headers=HEADERS).status_code == 403
    assert AUB_FACT["title"] not in titles_seen_by(data, OTHER)


# -------------------------------------------------------------- F-163


def shared_store() -> KnowHowStore:
    store = KnowHowStore()
    store.backend.append(verified(item("kh-west-hall", scope=Scope.AUB, club_id=None)))
    return store


def test_a_club_version_of_a_shared_fact_stays_shared() -> None:
    store = shared_store()
    newer = item("kh-west-hall-2", statement="Book Green Field four weeks ahead through the reservation form.")
    p = proposal(newer, ProposalOp.UPDATE, target_item="kh-west-hall")
    store.submit(p)
    outcome = store.verify(VerifyRequest(proposal=p, decision=VerifyDecision.ACCEPT), actor(Role.PRESIDENT), NOW)
    assert outcome.data is not None and outcome.data.committed is not None
    assert outcome.data.committed.scope is Scope.AUB and outcome.data.committed.club_id is None
    assert [i.item_id for i in store.visible(OTHER)] == ["kh-west-hall"]


def test_only_a_president_changes_a_shared_fact() -> None:
    store = shared_store()
    p = proposal(item("kh-west-hall-2"), ProposalOp.UPDATE, target_item="kh-west-hall")
    store.submit(p)
    with pytest.raises(CapabilityError):
        store.verify(VerifyRequest(proposal=p, decision=VerifyDecision.ACCEPT), actor(Role.TREASURER), NOW)
