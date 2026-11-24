"""T-46: connecting a club's Google Calendar in the app, keeping the key locked, and giving the cabinet read-only
access. A fake Google (an httpx mock) stands in for the real one. Synthetic people only."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from clubops.api.app import ApiConfig, create_app
from clubops.calendar.connect import SCOPES
from clubops.calendar.service import CalendarSettings
from tests import test_api as base
from tests.test_api import HEADERS, NOW, Scripts, plan, sign_in

data_dir = base.data_dir
scripts = base.scripts
CALENDARS = {"running-club": "calendar-running-club", "asme": "calendar-asme"}
APP = {"client_id": "id-1", "client_secret": "secret-1", "redirect_uri": "https://clubops.test/api/calendar/callback"}
HOST_KEY = {**APP, "refresh_token": "host-refresh"}
PRESIDENT, EVENTS, ADVISER, OTHER = "tp01@mail.aub.edu", "te02@mail.aub.edu", "ta03@aub.edu.lb", "op04@mail.aub.edu"


class FakeGoogle:
    def __init__(self) -> None:
        self.valid = {"host-refresh"}  # refresh tokens Google still honours
        self.role = "owner"  # what the connecting account is on the club calendar
        self.down = False
        self.refreshed: list[str] = []
        self.revoked: list[str] = []
        self.acl: dict[str, str] = {}
        self.acl_calls: list[tuple[str, str, str]] = []  # method, address, role sent
        self.writes: list[str] = []

    def exchange(self, code: str) -> httpx.Response:
        both = " ".join(SCOPES)
        if code == "good":
            self.valid.add("app-refresh")
            return httpx.Response(200, json={"refresh_token": "app-refresh", "access_token": "at", "scope": both})
        if code == "one-scope":
            return httpx.Response(200, json={"refresh_token": "r2", "access_token": "at", "scope": SCOPES[0]})
        if code == "no-refresh":
            return httpx.Response(200, json={"access_token": "at", "scope": both})
        return httpx.Response(400, json={"error": "invalid_grant"})

    def transport(self) -> httpx.MockTransport:
        def handle(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if request.url.host == "oauth2.googleapis.com":
                form = parse_qs(request.content.decode())
                if path == "/revoke":
                    self.revoked.append(form["token"][0])
                    return httpx.Response(200)
                if form["grant_type"] == ["authorization_code"]:
                    return self.exchange(form["code"][0])
                token = form["refresh_token"][0]
                self.refreshed.append(token)
                if token not in self.valid:
                    return httpx.Response(400, json={"error": "invalid_grant"})
                return httpx.Response(200, json={"access_token": "short-lived"})
            if self.down:
                return httpx.Response(503, json={})
            if "/calendarList/" in path:
                return httpx.Response(200, json={"accessRole": self.role})
            if "/acl" in path:
                return self.handle_acl(request)
            self.writes.append(path)
            return httpx.Response(200, json={})

        return httpx.MockTransport(handle)

    def handle_acl(self, request: httpx.Request) -> httpx.Response:
        import json

        path = request.url.path
        if path.endswith("/acl"):  # a new rule
            body = json.loads(request.content)
            address = body["scope"]["value"]
            self.acl_calls.append(("POST", address, body["role"]))
            self.acl[address] = body["role"]
            return httpx.Response(200, json=body)
        address = path.rsplit("user%3A", 1)[-1] if "user%3A" in path else path.rsplit("user:", 1)[-1]
        self.acl_calls.append((request.method, address, ""))
        if request.method == "GET":
            return httpx.Response(200, json={"role": self.acl[address]}) if address in self.acl else httpx.Response(404)
        self.acl.pop(address, None)
        return httpx.Response(204)


@pytest.fixture
def google() -> FakeGoogle:
    return FakeGoogle()


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


def make(data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock, settings: CalendarSettings) -> TestClient:
    config = ApiConfig(
        data_dir=data_dir,
        session_secret="test-secret",  # noqa: S106 (test only)
        dev_login=True,
        cookie_secure=False,
        calendar=settings,
    )
    return TestClient(create_app(config, scripts.factory(), clock=clock, calendar_transport=google.transport()))


@pytest.fixture
def client(data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock) -> Iterator[TestClient]:
    with make(data_dir, scripts, google, clock, CalendarSettings(CALENDARS, **APP)) as c:
        yield c


def state_of(c: TestClient) -> str:
    url = c.post("/api/calendar/connect", headers=HEADERS).json()["url"]
    return str(parse_qs(urlparse(url).query)["state"][0])


def callback(c: TestClient, state: str, code: str = "good") -> str:
    reply = c.get(f"/api/calendar/callback?state={state}&code={code}", follow_redirects=False)
    assert reply.status_code == 303, reply.text
    return str(reply.headers["location"])


def stored(data_dir: Path) -> list[bytes]:
    with closing(sqlite3.connect(data_dir / "calendar-auth.db")) as db:
        return [bytes(r[0]) for r in db.execute("SELECT token FROM connection")]


def connect(c: TestClient) -> None:
    sign_in(c, PRESIDENT)
    assert callback(c, state_of(c)).endswith("google=connected")


def approve(c: TestClient, scripts: Scripts) -> None:
    event_id = str(c.get(f"/api/runs/{plan(c, scripts)}").json()["event_id"])
    revision = c.get(f"/api/events/{event_id}").json()["revision"]
    assert (
        c.post(f"/api/events/{event_id}/approve-plan", json={"revision": revision}, headers=HEADERS).status_code == 200
    )


# ------------------------------------------------------------ who may connect


def test_only_the_president_can_connect_or_disconnect_and_only_the_cabinet_sees_the_state(
    client: TestClient,
) -> None:
    assert client.post("/api/calendar/connect", headers=HEADERS).status_code == 401
    assert client.get("/api/calendar/connection").status_code == 401
    assert client.get("/api/calendar/callback?state=x&code=y", follow_redirects=False).status_code == 401
    sign_in(client, EVENTS)  # a cabinet member who is not the president
    assert client.get("/api/calendar/connection").status_code == 200
    for call in (client.post, client.delete):
        assert call("/api/calendar/connect", headers=HEADERS).status_code == 403
    assert client.post("/api/calendar/share-cabinet", headers=HEADERS).status_code == 403
    assert client.get("/api/calendar/callback?state=x&code=y", follow_redirects=False).status_code == 403
    client.post("/api/auth/logout", headers=HEADERS)
    sign_in(client, ADVISER)
    assert client.get("/api/calendar/connection").status_code == 403


def test_the_connect_address_asks_for_exactly_the_two_calendar_permissions(client: TestClient) -> None:
    sign_in(client, PRESIDENT)
    url = client.post("/api/calendar/connect", headers=HEADERS).json()["url"]
    query = parse_qs(urlparse(url).query)
    assert urlparse(url).netloc == "accounts.google.com"
    assert query["scope"] == [" ".join(SCOPES)] and query["access_type"] == ["offline"]
    assert query["include_granted_scopes"] == ["false"] and query["redirect_uri"] == [APP["redirect_uri"]]
    assert len(query["state"][0]) >= 32 and "secret-1" not in url


def test_connect_says_not_set_up_when_the_host_has_no_google_app(
    data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock
) -> None:
    with make(data_dir, scripts, google, clock, CalendarSettings(CALENDARS)) as c:
        sign_in(c, PRESIDENT)
        assert c.post("/api/calendar/connect", headers=HEADERS).status_code == 501
        assert c.get("/api/calendar/connection").json()["state"] == "not_set_up"


# ------------------------------------------------------- the connect flow


def test_connecting_keeps_the_key_locked_and_the_plan_syncs_with_it(
    client: TestClient, scripts: Scripts, google: FakeGoogle, data_dir: Path
) -> None:
    sign_in(client, PRESIDENT)
    assert client.get("/api/calendar/connection").json() == {
        "state": "not_connected",
        "source": None,
        "can_connect": True,
        "access_changes_waiting": 0,
    }
    assert callback(client, state_of(client)) == "/calendar?google=connected"
    assert client.get("/api/calendar/connection").json()["state"] == "connected"
    (token,) = stored(data_dir)
    assert b"app-refresh" not in token and b"app-refresh" not in (data_dir / "calendar-auth.db").read_bytes()
    approve(client, scripts)
    assert google.writes and set(google.refreshed) == {"app-refresh"}  # the connected key, not the host's
    assert client.get("/api/calendar/sync").json() == {"connected": True, "waiting": 0, "problem": None}
    shown = client.get("/api/calendar/connection").text + client.get("/api/calendar/sync").text
    assert "app-refresh" not in shown and "calendar-running-club" not in shown


def test_a_connect_link_works_once_for_the_person_who_pressed_it(
    client: TestClient, data_dir: Path, google: FakeGoogle
) -> None:
    sign_in(client, PRESIDENT)
    state = state_of(client)
    assert callback(client, state).endswith("google=connected")
    assert callback(client, state).endswith("google=failed")  # replay
    assert callback(client, "forged-" + state).endswith("google=failed")
    client.delete("/api/calendar/connect", headers=HEADERS)
    stolen = state_of(client)
    client.post("/api/auth/logout", headers=HEADERS)
    sign_in(client, OTHER)  # another club's president cannot finish this link
    assert callback(client, stolen).endswith("google=failed")
    assert stored(data_dir) == []
    assert client.get("/api/calendar/connection").json()["state"] == "not_connected"


def test_a_connect_link_expires_after_ten_minutes(client: TestClient, clock: Clock, data_dir: Path) -> None:
    sign_in(client, PRESIDENT)
    state = state_of(client)
    clock.now += timedelta(minutes=11)
    assert callback(client, state).endswith("google=failed") and stored(data_dir) == []


@pytest.mark.parametrize("code", ["one-scope", "no-refresh", "bad-code"])
def test_nothing_is_kept_unless_google_gave_a_key_with_both_permissions(
    client: TestClient, data_dir: Path, code: str
) -> None:
    sign_in(client, PRESIDENT)
    assert callback(client, state_of(client), code).endswith("google=failed")
    assert stored(data_dir) == []


def test_an_account_that_does_not_own_the_calendar_is_refused(
    client: TestClient, google: FakeGoogle, data_dir: Path
) -> None:
    google.role = "reader"
    sign_in(client, PRESIDENT)
    assert callback(client, state_of(client)).endswith("google=failed") and stored(data_dir) == []


def test_a_person_who_says_no_on_googles_screen_ends_on_the_calendar_screen(client: TestClient) -> None:
    sign_in(client, PRESIDENT)
    reply = client.get("/api/calendar/callback?error=access_denied&state=x", follow_redirects=False)
    assert reply.status_code == 303 and reply.headers["location"] == "/calendar?google=denied"


def test_disconnecting_forgets_the_key_cancels_it_and_keeps_the_queue(
    client: TestClient, scripts: Scripts, google: FakeGoogle, data_dir: Path
) -> None:
    connect(client)
    google.down = True
    approve(client, scripts)
    waiting = client.get("/api/calendar/sync").json()["waiting"]
    assert waiting >= 2
    assert client.delete("/api/calendar/connect", headers=HEADERS).status_code == 204
    assert stored(data_dir) == [] and google.revoked == ["app-refresh"]
    status = client.get("/api/calendar/sync").json()
    assert status["connected"] is False and status["waiting"] == waiting  # nothing lost, nothing sent


def test_a_key_google_ended_asks_for_a_reconnect_and_never_falls_back_to_the_host_key(
    data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock
) -> None:
    with make(data_dir, scripts, google, clock, CalendarSettings(CALENDARS, **HOST_KEY)) as c:
        connect(c)
        google.valid.discard("app-refresh")  # the president revoked it in their Google account
        approve(c, scripts)
        status = c.get("/api/calendar/sync").json()
        assert (
            status["connected"] is False
            and status["waiting"] >= 2
            and "connect Google Calendar again" in status["problem"]
        )
        assert c.get("/api/calendar/connection").json()["state"] == "reconnect"
        assert google.writes == [] and "host-refresh" not in google.refreshed
        assert callback(c, state_of(c)).endswith("google=connected")  # reconnecting sends the waiting items
        assert c.post("/api/calendar/sync", headers=HEADERS).json() == {
            "connected": True,
            "waiting": 0,
            "problem": None,
        }
        assert google.writes


def test_a_changed_token_key_means_reconnect_not_a_crash(
    client: TestClient, scripts: Scripts, data_dir: Path, google: FakeGoogle, clock: Clock
) -> None:
    connect(client)
    other = CalendarSettings(CALENDARS, token_key="x" * 43 + "=", **APP)
    with make(data_dir, scripts, google, clock, other) as c:
        sign_in(c, PRESIDENT)
        approve(c, scripts)
        assert c.get("/api/calendar/connection").json()["state"] == "reconnect"
        assert google.writes == []


# ------------------------------------------------- cabinet reader access


def test_adding_a_cabinet_member_gives_reader_access_only_and_removing_takes_it_back(
    client: TestClient, google: FakeGoogle
) -> None:
    connect(client)
    added = client.post(
        "/api/cabinet",
        json={"name": "New Treasurer", "email": "nt05@mail.aub.edu", "role": "treasurer"},
        headers=HEADERS,
    )
    assert added.status_code == 201
    assert google.acl == {"nt05@mail.aub.edu": "reader"}
    assert {role for _, _, role in google.acl_calls if role} == {"reader"}  # never writer or owner
    client.post(
        "/api/cabinet", json={"name": "Some Adviser", "email": "sa06@aub.edu.lb", "role": "adviser"}, headers=HEADERS
    )
    assert "sa06@aub.edu.lb" not in google.acl  # an adviser is not cabinet
    assert (
        client.request(
            "DELETE", "/api/cabinet", json={"member_id": added.json()["member_id"]}, headers=HEADERS
        ).status_code
        == 204
    )
    assert google.acl == {}


def test_a_google_outage_keeps_the_access_change_and_a_retry_applies_it_once(
    client: TestClient, google: FakeGoogle
) -> None:
    connect(client)
    google.down = True
    client.post(
        "/api/cabinet",
        json={"name": "New Treasurer", "email": "nt05@mail.aub.edu", "role": "treasurer"},
        headers=HEADERS,
    )
    assert google.acl == {} and client.get("/api/calendar/connection").json()["access_changes_waiting"] == 1
    google.down = False
    client.post("/api/calendar/sync", headers=HEADERS)
    assert google.acl == {"nt05@mail.aub.edu": "reader"}
    assert client.get("/api/calendar/connection").json()["access_changes_waiting"] == 0
    posts = len([c for c in google.acl_calls if c[0] == "POST"])
    client.post("/api/calendar/sync", headers=HEADERS)
    assert len([c for c in google.acl_calls if c[0] == "POST"]) == posts == 1


def test_access_that_is_not_reader_is_left_alone_and_reported(client: TestClient, google: FakeGoogle) -> None:
    connect(client)
    google.acl["nt05@mail.aub.edu"] = "writer"  # someone gave this address more access by hand
    client.post(
        "/api/cabinet",
        json={"name": "New Treasurer", "email": "nt05@mail.aub.edu", "role": "treasurer"},
        headers=HEADERS,
    )
    assert google.acl == {"nt05@mail.aub.edu": "writer"}  # ClubOps changed nothing
    assert client.get("/api/calendar/connection").json()["access_changes_waiting"] == 1


def test_share_cabinet_queues_the_current_cabinet_for_reader_access(client: TestClient, google: FakeGoogle) -> None:
    connect(client)
    assert client.post("/api/calendar/share-cabinet", headers=HEADERS).json() == {"queued": 2}
    assert google.acl == {PRESIDENT: "reader", EVENTS: "reader"}  # not the adviser


def test_a_club_without_a_calendar_asks_google_for_nothing(
    data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock
) -> None:
    with make(data_dir, scripts, google, clock, CalendarSettings({"asme": "calendar-asme"}, **HOST_KEY)) as c:
        sign_in(c, PRESIDENT)
        c.post(
            "/api/cabinet",
            json={"name": "New Treasurer", "email": "nt05@mail.aub.edu", "role": "treasurer"},
            headers=HEADERS,
        )
        assert google.acl_calls == [] and c.get("/api/calendar/connection").json()["state"] == "not_set_up"
