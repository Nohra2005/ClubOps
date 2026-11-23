"""Backend side of the Google calendar sync (T-46): hand approved items to Joey's durable queue, drain it to
Google, and say what is waiting. Nothing here calls the model, and nothing runs for an unapproved plan.

The Calendar key is separate from the Gmail key and from Google sign-in (D-116). Until the in-app connect flow
exists, a person puts the key in the host's private settings; the browser never sees it."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from clubops.calendar.config import calendar_ids_from_json
from clubops.calendar.queue import SyncQueue
from clubops.calendar.sync import CalendarSync, GoogleCalendarGateway
from clubops.contracts.calendar import CalendarItem
from clubops.contracts.common import CABINET_ROLES, Role

TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - a public endpoint, not a secret
QUEUE_FILE = "calendar-sync.db"  # private host data, never in the repository
RENEW_HINT = (
    "The Calendar key expired or was revoked. In Testing mode Google cancels it every 7 days: "
    "get a new refresh token and replace CLUBOPS_CALENDAR_REFRESH_TOKEN on the host."
)


class CalendarKeyError(RuntimeError):
    """The Calendar key is missing, expired or revoked; a person must renew it."""


@dataclass(frozen=True)
class CalendarSettings:
    """The host's private Calendar settings. Any missing part means "not connected"."""

    calendar_ids: Mapping[str, str]
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None

    @property
    def has_key(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)


def settings_from_env(values: Mapping[str, str]) -> CalendarSettings:
    return CalendarSettings(
        calendar_ids=calendar_ids_from_json(values.get("CLUBOPS_GOOGLE_CALENDAR_IDS_JSON", "")),
        client_id=values.get("CLUBOPS_CALENDAR_CLIENT_ID") or None,
        client_secret=values.get("CLUBOPS_CALENDAR_CLIENT_SECRET") or None,
        refresh_token=values.get("CLUBOPS_CALENDAR_REFRESH_TOKEN") or None,
    )


def access_token(settings: CalendarSettings, *, transport: httpx.BaseTransport | None = None) -> str:
    """Exchange the saved refresh token for a short-lived access token."""
    if not settings.has_key:
        raise CalendarKeyError("The Calendar key is not set on the host.")
    with httpx.Client(transport=transport, timeout=15) as client:
        response = client.post(
            TOKEN_URL,
            data={
                "client_id": settings.client_id,
                "client_secret": settings.client_secret,
                "refresh_token": settings.refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code in (400, 401):
        raise CalendarKeyError(RENEW_HINT)
    response.raise_for_status()
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise CalendarKeyError("Google returned no access token.")
    return token


def cabinet_addresses(data_dir: Path, club_id: str) -> dict[Role, str]:
    """The club's private role directory: one address per cabinet role. Never taken from mail or the browser."""
    database = data_dir / "general.db"
    if not database.is_file():
        return {}
    with closing(sqlite3.connect(database)) as db:
        try:
            rows = db.execute("SELECT email, role FROM members WHERE club_id = ? ORDER BY rowid", (club_id,)).fetchall()
        except sqlite3.OperationalError:
            return {}
    addresses: dict[Role, str] = {}
    for email, role in rows:
        try:
            parsed = Role(str(role))
        except ValueError:
            continue
        if parsed in CABINET_ROLES:
            addresses.setdefault(parsed, str(email))
    return addresses


class CalendarService:
    def __init__(
        self, data_dir: Path, settings: CalendarSettings, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        self.data_dir = data_dir
        self.settings = settings
        self.transport = transport
        self.queue = SyncQueue(data_dir / QUEUE_FILE)
        self._lock = threading.Lock()  # one drain at a time: there is a single worker (README, J-23)
        self.problem: str | None = None  # the last drain's problem, shown in the status until a drain works

    def has_calendar(self, club_id: str) -> bool:
        return club_id in self.settings.calendar_ids

    def enqueue_approved(self, items: list[CalendarItem]) -> int:
        """Queue items of an approved plan for a club that has a calendar. Returns how many were queued."""
        queued = 0
        for item in items:
            if self.has_calendar(item.club_id):
                self.queue.enqueue(item, approved=True)
                queued += 1
        return queued

    def drain(self) -> str | None:
        """Send what is waiting. Returns a short problem text, or ``None``. A failure leaves work queued."""
        self.problem = self._drain()
        return self.problem

    def _drain(self) -> str | None:
        if not self.queue.pending():
            return None
        if not self.settings.has_key:
            return "The Calendar key is not set on the host."
        with self._lock:
            try:
                token = access_token(self.settings, transport=self.transport)
                sync = CalendarSync(GoogleCalendarGateway(token, transport=self.transport), self.settings.calendar_ids)
                self.queue.drain(sync, lambda club_id: cabinet_addresses(self.data_dir, club_id))
            except CalendarKeyError as exc:
                return str(exc)
            except (OSError, httpx.HTTPError):
                return "Google could not be reached. The calendar will retry."
            except ValueError:
                return "A calendar setting or a cabinet address is missing or invalid. Fix it, then retry."
        return None

    def status(self, club_id: str) -> dict[str, Any]:
        """Own-club status only: is it connected, how many items wait, and the last problem."""
        with closing(sqlite3.connect(self.queue.path)) as db:
            rows = db.execute("SELECT last_error FROM pending_calendar WHERE club_id = ?", (club_id,)).fetchall()
        errors = [str(r[0]) for r in rows if r[0]]
        return {
            "connected": self.settings.has_key and self.has_calendar(club_id),
            "waiting": len(rows),
            "problem": self.problem or (errors[0] if errors else None),
        }
