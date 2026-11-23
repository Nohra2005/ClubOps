"""T-46: an approved plan reaches the club's shared Google calendar through Joey's queue; nothing else does.
A fake Google (an httpx mock) stands in for the real one. Synthetic people and events only."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from clubops.api.app import ApiConfig, create_app
from clubops.calendar.service import CalendarSettings, cabinet_addresses, settings_from_env
from clubops.contracts.common import Role
from tests import test_api as base
from tests.test_api import HEADERS, NOW, Scripts, plan, sign_in

data_dir = base.data_dir  # the fixtures of the API tests: a rulebook and a small cabinet
scripts = base.scripts
CALENDARS = {"running-club": "calendar-running-club"}
KEY = {"client_id": "id-1", "client_secret": "secret-1", "refresh_token": "refresh-1"}


class FakeGoogle:
    """Records writes; ``down`` makes the calendar API fail; ``revoked`` makes the key fail."""

    def __init__(self) -> None:
        self.down = False
        self.revoked = False
        self.writes: list[tuple[str, str]] = []

    def transport(self) -> httpx.MockTransport:
        def handle(request: httpx.Request) -> httpx.Response:
            if request.url.host == "oauth2.googleapis.com":
                if self.revoked:
                    return httpx.Response(400, json={"error": "invalid_grant"})
                return httpx.Response(200, json={"access_token": "short-lived"})
            if self.down:
                return httpx.Response(503, json={})
            self.writes.append((request.method, request.url.path))
            return httpx.Response(200, json={})

        return httpx.MockTransport(handle)

    def event_ids(self) -> set[str]:
        return {path.rsplit("/", 1)[-1] for method, path in self.writes if method == "PUT"}


@pytest.fixture
def google() -> FakeGoogle:
    return FakeGoogle()


def make(data_dir: Path, scripts: Scripts, google: FakeGoogle, settings: CalendarSettings) -> TestClient:
    config = ApiConfig(
        data_dir=data_dir,
        session_secret="test-secret",  # noqa: S106 (test only)
        dev_login=True,
        cookie_secure=False,
        calendar=settings,
    )
    return TestClient(create_app(config, scripts.factory(), clock=lambda: NOW, calendar_transport=google.transport()))


@pytest.fixture
def client(data_dir: Path, scripts: Scripts, google: FakeGoogle) -> Iterator[TestClient]:
    with make(data_dir, scripts, google, CalendarSettings(CALENDARS, **KEY)) as c:
        yield c


def approve(c: TestClient, scripts: Scripts) -> str:
    sign_in(c)
    event_id = str(c.get(f"/api/runs/{plan(c, scripts)}").json()["event_id"])
    revision = c.get(f"/api/events/{event_id}").json()["revision"]
    reply = c.post(f"/api/events/{event_id}/approve-plan", json={"revision": revision}, headers=HEADERS)
    assert reply.status_code == 200, reply.text
    return event_id


def test_an_approved_plan_reaches_the_club_calendar(client: TestClient, scripts: Scripts, google: FakeGoogle) -> None:
    approve(client, scripts)
    assert len(google.event_ids()) >= 2  # the event and the impact-form task, plus reminders
    assert client.get("/api/calendar/sync").json() == {"connected": True, "waiting": 0, "problem": None}


def test_an_unapproved_or_stale_plan_never_reaches_google(
    client: TestClient, scripts: Scripts, google: FakeGoogle
) -> None:
    sign_in(client)
    event_id = str(client.get(f"/api/runs/{plan(client, scripts)}").json()["event_id"])
    stale = client.post(f"/api/events/{event_id}/approve-plan", json={"revision": 99}, headers=HEADERS)
    assert stale.status_code == 409
    assert client.post("/api/calendar/sync", headers=HEADERS).json()["waiting"] == 0
    assert google.writes == []  # a plan that was only drafted, or whose revision is old, is never sent


def test_a_google_outage_keeps_the_items_and_a_retry_sends_each_once(
    client: TestClient, scripts: Scripts, google: FakeGoogle
) -> None:
    google.down = True
    approve(client, scripts)
    waiting = client.get("/api/calendar/sync").json()
    assert waiting["waiting"] >= 2 and "retry later" in waiting["problem"] and google.writes == []
    assert "calendar-running-club" not in str(waiting)  # the private calendar id never reaches the browser
    google.down = False
    retried = client.post("/api/calendar/sync", headers=HEADERS).json()
    assert retried == {"connected": True, "waiting": 0, "problem": None}
    first = list(google.writes)
    assert client.post("/api/calendar/sync", headers=HEADERS).json()["waiting"] == 0
    assert google.writes == first  # nothing is sent twice; the stable ids keep one copy in Google
    assert len(google.event_ids()) == len({p for _, p in first if _ == "PUT"})


def test_a_revoked_key_is_reported_and_the_work_stays_queued(
    client: TestClient, scripts: Scripts, google: FakeGoogle
) -> None:
    google.revoked = True
    approve(client, scripts)
    status = client.get("/api/calendar/sync").json()
    assert status["waiting"] >= 2 and "expired or was revoked" in status["problem"]
    google.revoked = False
    assert client.post("/api/calendar/sync", headers=HEADERS).json() == {
        "connected": True,
        "waiting": 0,
        "problem": None,
    }


def test_without_a_key_approval_still_works_and_the_status_says_not_connected(
    data_dir: Path, scripts: Scripts, google: FakeGoogle
) -> None:
    with make(data_dir, scripts, google, CalendarSettings(CALENDARS)) as c:
        approve(c, scripts)
        status = c.get("/api/calendar/sync").json()
        assert status["connected"] is False and status["waiting"] >= 2 and "not set" in status["problem"]
        assert google.writes == []


def test_a_club_without_a_calendar_queues_nothing(data_dir: Path, scripts: Scripts, google: FakeGoogle) -> None:
    with make(data_dir, scripts, google, CalendarSettings({"asme": "calendar-asme"}, **KEY)) as c:
        approve(c, scripts)
        assert c.get("/api/calendar/sync").json() == {"connected": False, "waiting": 0, "problem": None}
        assert google.writes == []


def test_the_sync_routes_need_a_signed_in_cabinet_member(data_dir: Path, scripts: Scripts, google: FakeGoogle) -> None:
    with make(data_dir, scripts, google, CalendarSettings(CALENDARS, **KEY)) as c:
        assert c.get("/api/calendar/sync").status_code == 401
        assert c.post("/api/calendar/sync", headers=HEADERS).status_code == 401
        sign_in(c, "ta03@aub.edu.lb")  # an adviser is not a cabinet member
        assert c.get("/api/calendar/sync").status_code == 403
        assert c.post("/api/calendar/sync", headers=HEADERS).status_code == 403


def test_a_second_club_does_not_see_the_first_clubs_queue(data_dir: Path, scripts: Scripts, google: FakeGoogle) -> None:
    with make(data_dir, scripts, google, CalendarSettings(CALENDARS, **KEY)) as c:
        google.down = True
        approve(c, scripts)
        assert c.get("/api/calendar/sync").json()["waiting"] >= 2
        c.post("/api/auth/logout", headers=HEADERS)
        sign_in(c, "op04@mail.aub.edu")
        assert c.get("/api/calendar/sync").json() == {"connected": False, "waiting": 0, "problem": None}


def test_attendees_come_only_from_the_private_cabinet_directory(data_dir: Path) -> None:
    found = cabinet_addresses(data_dir, "running-club")
    assert found == {Role.PRESIDENT: "tp01@mail.aub.edu", Role.EVENTS: "te02@mail.aub.edu"}  # no adviser
    assert cabinet_addresses(data_dir, "no-such-club") == {}


def test_settings_are_read_from_private_env_values() -> None:
    values = {
        "CLUBOPS_GOOGLE_CALENDAR_IDS_JSON": '{"running-club": "id-x"}',
        "CLUBOPS_CALENDAR_CLIENT_ID": "a",
        "CLUBOPS_CALENDAR_CLIENT_SECRET": "b",
    }
    settings = settings_from_env(values)
    assert settings.calendar_ids == {"running-club": "id-x"} and not settings.has_key  # the refresh token is missing
    assert settings_from_env({**values, "CLUBOPS_CALENDAR_REFRESH_TOKEN": "c"}).has_key
