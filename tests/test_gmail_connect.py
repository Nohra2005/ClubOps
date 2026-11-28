"""T-47: connecting the ClubOps Gmail inbox in the app, keeping the key locked, and fetching the inbox for free.
A fake Google (an httpx mock) stands in for the real one. Synthetic people and mail only."""

from __future__ import annotations

import base64
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
from clubops.gmail_connect import SCOPE, GmailSettings
from tests import test_api as base
from tests.test_api import HEADERS, NOW, Scripts, sign_in
from tests.test_inbox_routes import OSA, _mail

data_dir = base.data_dir
scripts = base.scripts
APP = {
    "client_id": "gmail-id",
    "client_secret": "gmail-secret",
    "redirect_uri": "https://clubops.test/api/inbox/gmail/callback",
}
SETTINGS = GmailSettings(**APP, operators=frozenset({"tp01@mail.aub.edu"}), osa_senders=frozenset({OSA}))
PRESIDENT, EVENTS, ADVISER = "tp01@mail.aub.edu", "te02@mail.aub.edu", "ta03@aub.edu.lb"
INBOX = "clubops.agent@gmail.com"


class FakeGoogle:
    def __init__(self) -> None:
        self.valid = {"host-refresh"}
        self.account = INBOX
        self.mails: dict[str, bytes] = {}
        self.refreshed: list[str] = []
        self.revoked: list[str] = []
        self.lists = 0

    def transport(self) -> httpx.MockTransport:
        def handle(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if request.url.host == "oauth2.googleapis.com":
                form = parse_qs(request.content.decode())
                if path == "/revoke":
                    self.revoked.append(form["token"][0])
                    return httpx.Response(200)
                if form["grant_type"] == ["authorization_code"]:
                    code = form["code"][0]
                    if code == "good":
                        self.valid.add("app-refresh")
                        return httpx.Response(
                            200, json={"refresh_token": "app-refresh", "access_token": "at", "scope": SCOPE}
                        )
                    if code == "other-scope":
                        return httpx.Response(
                            200, json={"refresh_token": "r2", "access_token": "at", "scope": "openid email"}
                        )
                    return httpx.Response(400, json={"error": "invalid_grant"})
                token = form["refresh_token"][0]
                self.refreshed.append(token)
                if token not in self.valid:
                    return httpx.Response(400, json={"error": "invalid_grant"})
                return httpx.Response(200, json={"access_token": "short-lived"})
            if path.endswith("/profile"):
                return httpx.Response(200, json={"emailAddress": self.account})
            if path.endswith("/messages"):
                self.lists += 1
                return httpx.Response(200, json={"messages": [{"id": m} for m in self.mails]})
            message_id = path.rsplit("/", 1)[-1]
            raw = base64.urlsafe_b64encode(self.mails[message_id]).decode()
            return httpx.Response(200, json={"raw": raw})

        return httpx.MockTransport(handle)


@pytest.fixture
def google() -> FakeGoogle:
    google = FakeGoogle()
    google.mails = {"m1": _mail("running-club", "Sponsor note")}
    return google


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


def make(data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock, settings: GmailSettings) -> TestClient:
    config = ApiConfig(
        data_dir=data_dir,
        session_secret="test-secret",  # noqa: S106 (test only)
        dev_login=True,
        cookie_secure=False,
        gmail=settings,
    )
    return TestClient(create_app(config, scripts.factory(), clock=clock, calendar_transport=google.transport()))


@pytest.fixture
def client(data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock) -> Iterator[TestClient]:
    with make(data_dir, scripts, google, clock, SETTINGS) as c:
        yield c


def state_of(c: TestClient) -> str:
    url = c.post("/api/inbox/gmail/connect", headers=HEADERS).json()["url"]
    return str(parse_qs(urlparse(url).query)["state"][0])


def callback(c: TestClient, state: str, code: str = "good") -> str:
    reply = c.get(f"/api/inbox/gmail/callback?state={state}&code={code}", follow_redirects=False)
    assert reply.status_code == 303, reply.text
    return str(reply.headers["location"])


def stored(data_dir: Path) -> list[bytes]:
    with closing(sqlite3.connect(data_dir / "calendar-auth.db")) as db:
        return [bytes(r[0]) for r in db.execute("SELECT token FROM connection WHERE club_id = 'gmail'")]


def connect(c: TestClient) -> None:
    sign_in(c, PRESIDENT)
    assert callback(c, state_of(c)).endswith("gmail=connected")


def test_only_an_operator_connects_and_only_the_cabinet_fetches(client: TestClient) -> None:
    assert client.get("/api/inbox/gmail").status_code == 401
    assert client.post("/api/inbox/fetch", headers=HEADERS).status_code == 401
    assert client.get("/api/inbox/gmail/callback?state=x&code=y", follow_redirects=False).status_code == 401
    sign_in(client, PRESIDENT)  # J-25: the inbox is a role feature; the secretary has it, Events does not
    secretary = {"name": "Synthetic Secretary", "email": "ts06@example.org", "role_key": "secretary"}
    assert client.post("/api/cabinet", json=secretary, headers=HEADERS).status_code == 201
    sign_in(client, "ts06@example.org")  # inbox feature, not an operator
    assert client.get("/api/inbox/gmail").json()["can_manage"] is False
    assert client.post("/api/inbox/gmail/connect", headers=HEADERS).status_code == 403
    assert client.delete("/api/inbox/gmail/connect", headers=HEADERS).status_code == 403
    assert client.get("/api/inbox/gmail/callback?state=x&code=y", follow_redirects=False).status_code == 403
    sign_in(client, EVENTS)  # cabinet, but its role has no inbox feature
    assert client.get("/api/inbox/gmail").status_code == 403
    assert client.post("/api/inbox/fetch", headers=HEADERS).status_code == 403
    client.post("/api/auth/logout", headers=HEADERS)
    sign_in(client, ADVISER)  # the adviser is not cabinet: no fetch, no state
    assert client.get("/api/inbox/gmail").status_code == 403
    assert client.post("/api/inbox/fetch", headers=HEADERS).status_code == 403


def test_connect_says_not_set_up_without_an_operator_list(
    data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock
) -> None:
    with make(data_dir, scripts, google, clock, GmailSettings(**APP)) as c:
        sign_in(c, PRESIDENT)
        assert c.get("/api/inbox/gmail").json()["state"] == "not_set_up"
        assert c.post("/api/inbox/gmail/connect", headers=HEADERS).status_code == 403  # nobody is an operator


def test_connect_asks_google_for_read_only_inbox_access_and_nothing_else(client: TestClient) -> None:
    sign_in(client, PRESIDENT)
    url = client.post("/api/inbox/gmail/connect", headers=HEADERS).json()["url"]
    query = parse_qs(urlparse(url).query)
    assert query["scope"] == [SCOPE] and query["access_type"] == ["offline"] and "gmail-secret" not in url


def test_connecting_keeps_the_key_locked_and_the_fetch_uses_it(
    client: TestClient, google: FakeGoogle, data_dir: Path
) -> None:
    sign_in(client, PRESIDENT)
    assert client.get("/api/inbox/gmail").json()["state"] == "not_connected"
    assert client.post("/api/inbox/fetch", headers=HEADERS).status_code == 409  # no key yet
    assert callback(client, state_of(client)) == "/inbox?gmail=connected"
    (token,) = stored(data_dir)
    assert b"app-refresh" not in token and b"app-refresh" not in (data_dir / "calendar-auth.db").read_bytes()
    counts = client.post("/api/inbox/fetch", headers=HEADERS).json()
    assert counts["queued"] == 1 and google.refreshed == ["app-refresh"]
    assert [m["subject"] for m in client.get("/api/inbox").json()] == ["FW: Sponsor note"]
    shown = client.get("/api/inbox/gmail").text + str(counts)
    assert "app-refresh" not in shown and "Sponsor" not in str(counts)  # counts only, never mail text


def test_a_connect_link_works_once_and_expires(client: TestClient, clock: Clock, data_dir: Path) -> None:
    sign_in(client, PRESIDENT)
    state = state_of(client)
    assert callback(client, state).endswith("gmail=connected")
    assert callback(client, state).endswith("gmail=failed")  # replay
    assert callback(client, "forged").endswith("gmail=failed")
    client.delete("/api/inbox/gmail/connect", headers=HEADERS)
    late = state_of(client)
    clock.now += timedelta(minutes=11)
    assert callback(client, late).endswith("gmail=failed") and stored(data_dir) == []


def test_nothing_is_kept_for_the_wrong_account_or_a_missing_permission(
    data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock
) -> None:
    only_inbox = GmailSettings(**APP, operators=SETTINGS.operators, osa_senders=SETTINGS.osa_senders, address=INBOX)
    with make(data_dir, scripts, google, clock, only_inbox) as c:
        sign_in(c, PRESIDENT)
        google.account = "someone.else@gmail.com"
        assert callback(c, state_of(c)).endswith("gmail=failed") and stored(data_dir) == []
        google.account = INBOX
        assert callback(c, state_of(c), "other-scope").endswith("gmail=failed") and stored(data_dir) == []
        assert callback(c, state_of(c), "bad-code").endswith("gmail=failed") and stored(data_dir) == []
        assert callback(c, state_of(c)).endswith("gmail=connected") and len(stored(data_dir)) == 1


def test_a_key_google_ended_asks_for_a_reconnect_and_never_uses_the_host_key(
    data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock
) -> None:
    with_host_key = GmailSettings(
        **APP,
        refresh_token="host-refresh",  # noqa: S106 (a made-up key)
        operators=SETTINGS.operators,
        osa_senders=SETTINGS.osa_senders,
    )
    with make(data_dir, scripts, google, clock, with_host_key) as c:
        sign_in(c, PRESIDENT)
        assert c.get("/api/inbox/gmail").json()["source"] == "host"  # the older pasted key still works
        connect(c)
        google.valid.discard("app-refresh")
        clock.now += timedelta(minutes=1)
        refused = c.post("/api/inbox/fetch", headers=HEADERS)
        assert refused.status_code == 409 and "connect the ClubOps inbox again" in refused.json()["detail"]
        assert c.get("/api/inbox/gmail").json()["state"] == "reconnect" and "host-refresh" not in google.refreshed
        assert callback(c, state_of(c)).endswith("gmail=connected")
        clock.now += timedelta(minutes=1)
        assert c.post("/api/inbox/fetch", headers=HEADERS).json()["queued"] == 1


def test_fetch_needs_the_osa_sender_list_and_two_quick_clicks_ask_gmail_once(
    data_dir: Path, scripts: Scripts, google: FakeGoogle, clock: Clock
) -> None:
    with make(data_dir, scripts, google, clock, GmailSettings(**APP, operators=SETTINGS.operators)) as c:
        connect(c)
        refused = c.post("/api/inbox/fetch", headers=HEADERS)
        assert refused.status_code == 409 and "OSA senders" in refused.json()["detail"] and google.lists == 0
    with make(data_dir, scripts, google, clock, SETTINGS) as c:
        sign_in(c, PRESIDENT)
        first = c.post("/api/inbox/fetch", headers=HEADERS).json()
        assert c.post("/api/inbox/fetch", headers=HEADERS).json() == first and google.lists == 1
        clock.now += timedelta(seconds=30)
        c.post("/api/inbox/fetch", headers=HEADERS)
        assert google.lists == 2


def test_disconnecting_forgets_and_cancels_the_key(client: TestClient, google: FakeGoogle, data_dir: Path) -> None:
    connect(client)
    assert client.delete("/api/inbox/gmail/connect", headers=HEADERS).status_code == 204
    assert stored(data_dir) == [] and google.revoked == ["app-refresh"]
    assert client.get("/api/inbox/gmail").json()["state"] == "not_connected"
