"""J-25: per-club roles with feature permissions, and operator-approved club sign-up (D-201).

Synthetic people and clubs only (example.org addresses); no Google call leaves the test (an httpx mock)."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from clubops.api import roles as perms
from clubops.api.app import ApiConfig, create_app
from clubops.api.roles import BASE_ROLES, TREASURER_GRANTS, ClubRoles
from clubops.api.security import MemberStore
from clubops.calendar.connect import AUTH_FILE
from clubops.calendar.service import CalendarSettings, cabinet_addresses
from clubops.contracts.common import Role
from clubops.gmail_connect import GmailSettings
from tests.test_api import HEADERS, NOW, Scripts

CLUB, OTHER_CLUB = "running-club", "asme"
EMAIL = {
    "president": "pres@example.org",
    "vice_president": "vp@example.org",
    "treasurer": "treas@example.org",
    "secretary": "sec@example.org",
    "social_media": "social@example.org",
}
ADVISER, OTHER = "adviser@example.org", "other-pres@example.org"
OPERATORS = frozenset({EMAIL["president"]})  # the host's operator is also a signed-in member (existing rule)
GRANTS = {b.key: b.features for b in BASE_ROLES}


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    people = MemberStore(tmp_path)
    for b in BASE_ROLES:
        people.add(CLUB, f"Synthetic {b.name}", EMAIL[b.key], b.label, b.key)
    people.add(CLUB, "Synthetic Adviser", ADVISER, Role.ADVISER)
    people.add(OTHER_CLUB, "Synthetic Other President", OTHER, Role.PRESIDENT)
    people.close()
    return tmp_path


def make(data_dir: Path, *, dev: bool = True, transport: httpx.BaseTransport | None = None) -> TestClient:
    config = ApiConfig(
        data_dir=data_dir,
        session_secret="test-secret",  # noqa: S106 (test only)
        dev_login=dev,
        cookie_secure=False,
        google_client_id="client-123",
        calendar=CalendarSettings({CLUB: "calendar-running"}),  # a calendar but no key: shares stay queued
        gmail=GmailSettings(operators=OPERATORS),
    )
    return TestClient(create_app(config, Scripts().factory(), clock=lambda: NOW, google_transport=transport))


@pytest.fixture
def client(data_dir: Path) -> Iterator[TestClient]:
    with make(data_dir) as c:
        yield c


def as_(c: TestClient, email: str) -> TestClient:
    r = c.post("/api/auth/dev", json={"email": email}, headers=HEADERS)
    assert r.status_code == 200, r.text
    return c


def shares(data_dir: Path) -> dict[str, str]:
    with closing(sqlite3.connect(data_dir / AUTH_FILE)) as db:
        return {str(e): str(a) for e, a in db.execute("SELECT email, action FROM sharing_pending")}


# ------------------------------------------------------- every mutating route has a permission

# Every POST/PATCH/PUT/DELETE route and who may call it. A new mutating route fails the guard until it is listed.
MUTATING: dict[tuple[str, str], str] = {
    ("POST", "/api/auth/google"): "public",
    ("POST", "/api/auth/dev"): "public",
    ("POST", "/api/auth/logout"): "public",
    ("POST", "/api/clubs/requests"): "public",  # proven by a Google token; no session, no club data
    ("POST", "/api/events/plan"): perms.PLAN_EVENTS,
    ("POST", "/api/events/{event_id}/rebuild"): perms.PLAN_EVENTS,
    ("POST", "/api/runs/{run_id}/answer"): perms.PLAN_EVENTS,
    ("POST", "/api/runs/{run_id}/continue"): perms.PLAN_EVENTS,
    ("PATCH", "/api/events/{event_id}"): perms.PLAN_EVENTS,
    ("POST", "/api/events/{event_id}/approve-plan"): perms.APPROVE_PLANS,
    ("PATCH", "/api/tasks/{task_id:path}"): perms.TASKS,
    ("POST", "/api/events/{event_id}/drafts/{draft_type}"): perms.DRAFTS,
    ("POST", "/api/chat/ask"): perms.CHAT,
    ("POST", "/api/chat/teach"): perms.CHAT,
    ("POST", "/api/documents"): perms.UPLOAD,
    ("POST", "/api/events/{event_id}/after-event"): perms.UPLOAD,
    ("POST", "/api/review/{proposal_id}"): perms.REVIEW_APPROVE,
    ("POST", "/api/knowledge/{item_id}/edit"): perms.KNOWLEDGE_EDIT,
    ("POST", "/api/knowledge/{item_id}/retire"): perms.KNOWLEDGE_EDIT,
    ("POST", "/api/knowledge/{item_id}/undo"): perms.KNOWLEDGE_EDIT,
    ("POST", "/api/inbox/fetch"): perms.INBOX,
    ("POST", "/api/inbox/{message_id}/allow"): perms.INBOX,
    ("POST", "/api/inbox/{message_id}/capture"): perms.INBOX,
    ("POST", "/api/calendar/sync"): perms.APPROVE_PLANS,
    ("POST", "/api/calendar/connect"): "president",
    ("DELETE", "/api/calendar/connect"): "president",
    ("POST", "/api/calendar/share-cabinet"): "president",
    ("POST", "/api/knowledge/{item_id}/restore"): "president",
    ("POST", "/api/cabinet"): "president",
    ("DELETE", "/api/cabinet"): "president",
    ("POST", "/api/roles"): "president",
    ("PATCH", "/api/roles/{key}"): "president",
    ("DELETE", "/api/roles/{key}"): "president",
    ("POST", "/api/setup/next"): "setup",  # the setup router checks president itself (C-21)
    ("POST", "/api/inbox/gmail/connect"): "operator",
    ("DELETE", "/api/inbox/gmail/connect"): "operator",
    ("GET", "/api/clubs/requests"): "operator",
    ("POST", "/api/clubs/requests/{request_id}/approve"): "operator",
    ("POST", "/api/clubs/requests/{request_id}/reject"): "operator",
}
# Feature-gated reads: the inbox screens and calendar connection state.
READS = {
    ("GET", "/api/inbox"): perms.INBOX,
    ("GET", "/api/inbox/skipped"): perms.INBOX,
}
DEPENDENCY = {"president": "president", "operator": "operator", "setup": "setup_actor"}


def _names(dependant: Any) -> set[str]:
    found = set()
    for d in dependant.dependencies:
        found.add(getattr(d.call, "__name__", ""))
        found |= _names(d)
    return found


def _flat(routes: list[Any]) -> list[APIRoute]:
    """FastAPI 0.16x keeps an included router (the setup route) as one entry; look inside it too."""
    found: list[APIRoute] = []
    for r in routes:
        inner = getattr(r, "original_router", None)
        found += _flat(inner.routes) if inner is not None else [r] if isinstance(r, APIRoute) else []
    return found


def _routes(c: TestClient) -> dict[tuple[str, str], APIRoute]:
    return {(m, r.path): r for r in _flat(c.app.routes) for m in r.methods}


def test_every_mutating_route_has_an_explicit_permission(client: TestClient) -> None:
    routes = _routes(client)
    changing = {k for k in routes if k[0] in {"POST", "PATCH", "PUT", "DELETE"}}
    listed = {k for k in MUTATING if k[0] != "GET"}
    assert changing - listed == set(), "a mutating route has no permission entry in MUTATING"
    assert listed - changing == set(), "MUTATING lists a route that no longer exists"
    for key, who in {**MUTATING, **READS}.items():
        names = _names(routes[key].dependant)
        if who == "public":
            assert "signed_in" not in names, key
        elif who in DEPENDENCY:
            assert DEPENDENCY[who] in names, key
        else:
            assert f"requires_{who}" in names, key
            assert "cabinet" not in names, key  # the old any-cabinet gate is gone from feature routes


def _allowed(who: str, role_key: str, email: str) -> bool:
    if who in perms.FEATURES:
        return who in GRANTS.get(role_key, frozenset())
    if who in {"president", "setup"}:
        return role_key == "president"
    return who == "operator" and email in OPERATORS


@pytest.mark.parametrize("role_key", [*EMAIL, "adviser"])
def test_each_base_role_meets_the_grant_table_on_every_route(client: TestClient, role_key: str) -> None:
    email = EMAIL.get(role_key, ADVISER)
    as_(client, email)
    wrong = []
    for (method, path), who in {**MUTATING, **READS}.items():
        if who == "public":
            continue
        url = re.sub(r"\{[^}]+\}", "x", path)
        kw: dict[str, Any] = {} if method == "GET" else {"headers": HEADERS, "json": {}}
        status = client.request(method, url, **kw).status_code
        assert status != 401, (method, path)
        if (status == 403) == _allowed(who, role_key, email):
            wrong.append((method, path, status))
    assert wrong == []


FEATURE_PROBE: dict[str, tuple[str, str, dict[str, Any] | None]] = {
    perms.PLAN_EVENTS: ("PATCH", "/api/events/ev-missing", {"fields": {}}),
    perms.APPROVE_PLANS: ("POST", "/api/events/ev-missing/approve-plan", {"revision": 1}),
    perms.TASKS: ("PATCH", "/api/tasks/ev-missing/osa", {"state": "done"}),
    perms.DRAFTS: ("POST", "/api/events/ev-missing/drafts/proposal", {}),
    perms.CHAT: ("POST", "/api/chat/ask", {"text": ""}),
    perms.UPLOAD: ("POST", "/api/documents", {}),
    perms.REVIEW_APPROVE: ("POST", "/api/review/p-missing", {"decision": "approve"}),
    perms.KNOWLEDGE_EDIT: ("POST", "/api/knowledge/kh-missing/retire", {}),
    perms.INBOX: ("GET", "/api/inbox", None),
    perms.CALENDAR_ACCESS: ("GET", "/api/calendar/connection", None),
}


@pytest.mark.parametrize("feature", perms.FEATURES)
@pytest.mark.parametrize("role_key", list(EMAIL))
def test_grant_table_feature_by_feature(client: TestClient, role_key: str, feature: str) -> None:
    as_(client, EMAIL[role_key])
    method, url, body = FEATURE_PROBE[feature]
    kw: dict[str, Any] = {} if body is None else {"headers": HEADERS, "json": body}
    status = client.request(method, url, **kw).status_code
    assert (status != 403) is (feature in GRANTS[role_key]), (role_key, feature, status)


def test_me_lists_the_features_and_role(client: TestClient) -> None:
    me = as_(client, EMAIL["secretary"]).get("/api/me").json()
    assert me["role"] == "secretary" and me["role_key"] == "secretary" and me["role_name"] == "Secretary"
    assert me["features"] == ["plan_events", "tasks", "drafts", "chat", "upload", "inbox", "calendar_access"]
    social = as_(client, EMAIL["social_media"]).get("/api/me").json()
    assert social["role"] == "communications" and social["role_name"] == "Social Media"
    adviser = as_(client, ADVISER).get("/api/me").json()
    assert adviser["features"] == [] and adviser["role_key"] == "adviser"
    assert as_(client, EMAIL["president"]).get("/api/me").json()["features"] == list(perms.FEATURES)


def test_everyone_signed_in_reads_the_roles(client: TestClient) -> None:
    listing = as_(client, ADVISER).get("/api/roles").json()
    assert [r["key"] for r in listing["roles"]] == [b.key for b in BASE_ROLES]
    assert all(r["base"] and not r["editable"] and r["holders"] == 1 for r in listing["roles"])
    assert listing["features"] == list(perms.FEATURES) and "president" not in listing["task_labels"]


# ---------------------------------------------------------------- custom roles


def test_custom_role_lifecycle_with_calendar_switch(client: TestClient, data_dir: Path) -> None:
    as_(client, EMAIL["treasurer"])
    assert client.post("/api/roles", json={"name": "Logistics"}, headers=HEADERS).status_code == 403
    as_(client, EMAIL["president"])
    made = client.post(
        "/api/roles",
        json={"name": "Logistics Lead", "features": ["plan_events", "calendar_access"], "task_label": "events"},
        headers=HEADERS,
    )
    assert made.status_code == 201, made.text
    assert made.json()["key"] == "logistics_lead" and made.json()["editable"] is True
    person = {"name": "Synthetic Logistics", "email": "logistics@example.org", "role_key": "logistics_lead"}
    assert client.post("/api/cabinet", json=person, headers=HEADERS).json()["role_name"] == "Logistics Lead"
    assert shares(data_dir)["logistics@example.org"] == "grant"  # its role has calendar access

    me = as_(client, "logistics@example.org").get("/api/me").json()
    assert me["features"] == ["plan_events", "calendar_access"] and me["role"] == "events"
    assert client.patch("/api/events/ev-missing", json={"fields": {}}, headers=HEADERS).status_code == 404
    assert client.post("/api/chat/ask", json={"text": "hello"}, headers=HEADERS).status_code == 403

    as_(client, EMAIL["president"])
    edited = client.patch("/api/roles/logistics_lead", json={"features": ["chat"]}, headers=HEADERS)
    assert edited.status_code == 200 and edited.json()["features"] == ["chat"]
    assert shares(data_dir)["logistics@example.org"] == "revoke"  # switching calendar off takes it back
    client.patch("/api/roles/logistics_lead", json={"features": ["chat", "calendar_access"]}, headers=HEADERS)
    assert shares(data_dir)["logistics@example.org"] == "grant"
    relabel = client.patch("/api/roles/logistics_lead", json={"task_label": "sponsorship"}, headers=HEADERS)
    assert relabel.json()["task_label"] == "sponsorship"
    assert as_(client, "logistics@example.org").get("/api/me").json()["role"] == "sponsorship"

    as_(client, EMAIL["president"])
    assert client.delete("/api/roles/logistics_lead", headers=HEADERS).status_code == 409  # still held
    holder = next(m for m in client.get("/api/cabinet").json() if m["email"] == "logistics@example.org")
    gone = client.request("DELETE", "/api/cabinet", json={"member_id": holder["member_id"]}, headers=HEADERS)
    assert gone.status_code == 204
    assert client.delete("/api/roles/logistics_lead", headers=HEADERS).status_code == 204
    assert "logistics_lead" not in [r["key"] for r in client.get("/api/roles").json()["roles"]]


def test_base_roles_and_president_powers_cannot_be_changed(client: TestClient) -> None:
    as_(client, EMAIL["president"])
    assert client.patch("/api/roles/treasurer", json={"features": ["inbox"]}, headers=HEADERS).status_code == 403
    assert client.delete("/api/roles/president", headers=HEADERS).status_code == 403
    for power in ("manage_members", "connect_calendar", "restore_knowledge"):
        refused = client.post("/api/roles", json={"name": "Shadow", "features": [power]}, headers=HEADERS)
        assert refused.status_code == 422
    for label in ("president", "member", "adviser"):
        refused = client.post("/api/roles", json={"name": "Shadow", "task_label": label}, headers=HEADERS)
        assert refused.status_code == 422
    assert client.post("/api/roles", json={"name": "President"}, headers=HEADERS).status_code == 409
    # Even with every feature, a custom role never manages members or the calendar connection.
    client.post("/api/roles", json={"name": "Everything", "features": list(perms.FEATURES)}, headers=HEADERS)
    person = {"name": "Synthetic Everything", "email": "all@example.org", "role_key": "everything"}
    assert client.post("/api/cabinet", json=person, headers=HEADERS).status_code == 201
    as_(client, "all@example.org")
    assert client.post("/api/cabinet", json={**person, "email": "x@example.org"}, headers=HEADERS).status_code == 403
    assert client.post("/api/calendar/share-cabinet", headers=HEADERS).status_code == 403
    assert client.delete("/api/calendar/connect", headers=HEADERS).status_code == 403
    assert client.post("/api/knowledge/kh-x/restore", json={}, headers=HEADERS).status_code == 403
    assert client.post("/api/roles", json={"name": "Another"}, headers=HEADERS).status_code == 403


def test_another_club_cannot_see_or_edit_a_custom_role(client: TestClient) -> None:
    as_(client, EMAIL["president"])
    client.post("/api/roles", json={"name": "Design", "features": ["upload"]}, headers=HEADERS)
    as_(client, OTHER)
    assert "design" not in [r["key"] for r in client.get("/api/roles").json()["roles"]]
    assert client.patch("/api/roles/design", json={"features": ["inbox"]}, headers=HEADERS).status_code == 404
    assert client.delete("/api/roles/design", headers=HEADERS).status_code == 404
    taken = {"name": "Synthetic Stray", "email": "stray@example.org", "role_key": "design"}
    assert client.post("/api/cabinet", json=taken, headers=HEADERS).status_code == 404


def test_old_cabinet_form_still_adds_members(client: TestClient, data_dir: Path) -> None:
    as_(client, EMAIL["president"])
    comms = {"name": "Synthetic Comms", "email": "comms@example.org", "role": "communications"}
    assert client.post("/api/cabinet", json=comms, headers=HEADERS).json()["role_key"] == "social_media"
    events = {"name": "Synthetic Events", "email": "events@example.org", "role": "events"}
    added = client.post("/api/cabinet", json=events, headers=HEADERS).json()
    assert added["role_key"] == "events" and added["role_name"] == "Events"
    adviser = {"name": "Synthetic Adviser Two", "email": "adviser2@example.org", "role_key": "adviser"}
    assert client.post("/api/cabinet", json=adviser, headers=HEADERS).json()["role"] == "adviser"
    assert "adviser2@example.org" not in shares(data_dir)  # no calendar access for the read-only adviser
    nobody = {"name": "Synthetic Member", "email": "member@example.org", "role": "member"}
    assert client.post("/api/cabinet", json=nobody, headers=HEADERS).status_code == 422
    assert client.post("/api/cabinet", json={**nobody, "role": None}, headers=HEADERS).status_code == 422


def test_custom_role_members_are_still_cabinet_actors(data_dir: Path) -> None:
    """Capabilities refuse non-cabinet actors (runner); a custom role's task label keeps its holders cabinet."""
    people = MemberStore(data_dir)
    roles = ClubRoles(data_dir, people)
    try:
        role = roles.create(CLUB, "Outreach", ["chat"], Role.SPONSORSHIP)
        member = people.add(CLUB, "Synthetic Outreach", "outreach@example.org", role.task_label, role.key)
        assert member.actor().is_cabinet and roles.features_for(member) == frozenset({"chat"})
    finally:
        roles.close()
        people.close()


# ---------------------------------------------------------------- club sign-up


def ask(c: TestClient, email: str = "founder@example.org", club: str = "Chess Society", **kw: Any) -> httpx.Response:
    body = {"name": "Synthetic Founder", "club_name": club, "email": email, **kw}
    return c.post("/api/clubs/requests", json=body, headers=HEADERS)


def test_club_request_approved_by_an_operator_creates_the_club(client: TestClient) -> None:
    asked = ask(client)
    assert asked.status_code == 201, asked.text
    assert asked.json()["status"] == "pending" and asked.json()["club_id"] == "chess-society"
    assert "clubops_session" not in asked.cookies  # no session for an unknown person
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/auth/dev", json={"email": "founder@example.org"}, headers=HEADERS).status_code == 403
    assert ask(client).status_code == 409  # one pending request per e-mail
    assert ask(client, email=EMAIL["treasurer"]).status_code == 409  # already a member somewhere

    as_(client, EMAIL["treasurer"])  # a member who is not an operator
    assert client.get("/api/clubs/requests").status_code == 403
    request_id = asked.json()["id"]
    assert client.post(f"/api/clubs/requests/{request_id}/approve", headers=HEADERS).status_code == 403

    as_(client, EMAIL["president"])  # the operator
    assert [r["id"] for r in client.get("/api/clubs/requests").json()] == [request_id]
    approved = client.post(f"/api/clubs/requests/{request_id}/approve", headers=HEADERS)
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert client.post(f"/api/clubs/requests/{request_id}/approve", headers=HEADERS).status_code == 409
    assert client.get("/api/clubs/requests").json() == []

    me = as_(client, "founder@example.org").get("/api/me").json()
    assert me["club"]["id"] == "chess-society" and me["role_key"] == "president"
    assert me["features"] == list(perms.FEATURES)
    assert [r["key"] for r in client.get("/api/roles").json()["roles"]] == [b.key for b in BASE_ROLES]
    assert [m["email"] for m in client.get("/api/cabinet").json()] == ["founder@example.org"]


def test_club_request_rejected_and_slug_kept_unique(client: TestClient) -> None:
    taken = ask(client, email="rival@example.org", club="Running Club")
    assert taken.json()["club_id"] == "running-club-2"  # an existing club keeps its slug
    as_(client, EMAIL["president"])
    rejected = client.post(f"/api/clubs/requests/{taken.json()['id']}/reject", headers=HEADERS)
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert client.post("/api/auth/dev", json={"email": "rival@example.org"}, headers=HEADERS).status_code == 403
    assert client.post("/api/clubs/requests/req-missing/approve", headers=HEADERS).status_code == 404
    again = ask(client, email="rival@example.org", club="Running Club")
    assert again.status_code == 201  # a rejected person may ask again
    assert ask(client, email="third@example.org", club="!!").status_code == 422


def test_production_club_request_needs_a_verified_google_token(data_dir: Path) -> None:
    def google(request: httpx.Request) -> httpx.Response:
        good = request.url.params.get("id_token") == "good-token-123"
        info = {"aud": "client-123", "email": "Founder@Example.org", "email_verified": "true"}
        return httpx.Response(200 if good else 400, json=info if good else {})

    with make(data_dir, dev=False, transport=httpx.MockTransport(google)) as c:
        assert ask(c).status_code == 403  # an e-mail alone proves nothing in production
        assert ask(c, credential="forged-token-123").status_code == 403
        made = ask(c, email=None, credential="good-token-123")
        assert made.status_code == 201 and made.json()["email"] == "founder@example.org"


# ---------------------------------------------------------------- migration


def old_members_file(data_dir: Path) -> None:
    """A general.db from before J-25: the role column only, every old label."""
    data_dir.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(data_dir / "general.db")) as db, db:
        db.execute(
            "CREATE TABLE members (member_id TEXT PRIMARY KEY, club_id TEXT NOT NULL, name TEXT NOT NULL, "
            "email TEXT NOT NULL UNIQUE, role TEXT NOT NULL)"
        )
        db.executemany(
            "INSERT INTO members VALUES (?, ?, ?, ?, ?)",
            [
                ("m-p", "old-club", "P", "p@example.org", "president"),
                ("m-c", "old-club", "C", "c@example.org", "communications"),
                ("m-e", "old-club", "E", "e@example.org", "events"),
                ("m-s", "old-club", "S", "s@example.org", "sponsorship"),
                ("m-t", "old-club", "T", "t@example.org", "treasurer"),
                ("m-a", "old-club", "A", "a@example.org", "adviser"),
            ],
        )


def test_migration_is_additive_idempotent_and_keeps_everyone_working(tmp_path: Path) -> None:
    old_members_file(tmp_path)
    before = cabinet_addresses(tmp_path, "old-club")
    for _ in range(2):  # twice: the second start changes nothing
        people = MemberStore(tmp_path)
        roles = ClubRoles(tmp_path, people)
        roles.migrate()
        roles.close()
        people.close()
    with closing(sqlite3.connect(tmp_path / "general.db")) as db:
        keys = dict(db.execute("SELECT member_id, role_key FROM members").fetchall())
        labels = dict(db.execute("SELECT member_id, role FROM members").fetchall())
        rows = db.execute("SELECT role_key, name, base FROM club_roles WHERE club_id = 'old-club'").fetchall()
    assert keys == {
        "m-p": "president",
        "m-c": "social_media",
        "m-e": "events",
        "m-s": "sponsorship",
        "m-t": "treasurer",
        "m-a": "adviser",
    }
    assert labels["m-c"] == "communications" and labels["m-e"] == "events"  # task labels untouched
    assert sorted(rows) == sorted(
        [(b.key, b.name, 1) for b in BASE_ROLES] + [("events", "Events", 0), ("sponsorship", "Sponsorship", 0)]
    )
    assert cabinet_addresses(tmp_path, "old-club") == before  # the calendar's role directory still reads it

    with make(tmp_path) as c:
        for email in ("p@example.org", "c@example.org", "e@example.org", "s@example.org", "t@example.org"):
            features = set(as_(c, email).get("/api/me").json()["features"])
            assert features >= TREASURER_GRANTS, email  # every old cabinet member keeps planning and calendar
        assert as_(c, "a@example.org").get("/api/me").json()["features"] == []
        assert as_(c, "e@example.org").get("/api/me").json()["role_name"] == "Events"


def test_a_member_added_outside_the_app_gets_their_role_lazily(client: TestClient, data_dir: Path) -> None:
    people = MemberStore(data_dir)
    people.add(OTHER_CLUB, "Synthetic Sponsor", "sponsor@example.org", Role.SPONSORSHIP)  # e.g. scripts/add_member
    people.close()
    me = as_(client, "sponsor@example.org").get("/api/me").json()
    assert me["role_key"] == "sponsorship" and set(me["features"]) == TREASURER_GRANTS
