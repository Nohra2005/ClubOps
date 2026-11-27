"""Backend side of the Google calendar sync (T-46): hand approved items to Joey's durable queue, drain it to
Google, and say what is waiting. Nothing here calls the model, and nothing runs for an unapproved plan.

The Calendar key is separate from the Gmail key and from Google sign-in (D-116). Until the in-app connect flow
exists, a person puts the key in the host's private settings; the browser never sees it."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from clubops.calendar.config import calendar_ids_from_json
from clubops.calendar.connect import REVOKE_URL, ConnectionVault, authorization_url, scopes_ok, token_key
from clubops.calendar.queue import SyncQueue
from clubops.calendar.sharing import GoogleCalendarSharing, SharingError
from clubops.calendar.sync import CalendarSync, GoogleCalendarGateway
from clubops.contracts.calendar import CalendarItem, DeadlineTask, DeadlineTasksRequest
from clubops.contracts.common import CABINET_ROLES, Role

TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - a public endpoint, not a secret
QUEUE_FILE = "calendar-sync.db"  # private host data, never in the repository
RENEW_HINT = (
    "The Calendar key expired or was revoked. In Testing mode Google cancels it every 7 days: "
    "get a new refresh token and replace CLUBOPS_CALENDAR_REFRESH_TOKEN on the host."
)
RECONNECT_HINT = "Google Calendar access ended. The president needs to connect Google Calendar again."
WRONG_ACCOUNT = "That Google account does not own this club's calendar. Sign in with the account that owns it."
CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/"  # + id + /acl: allowed by calendar.acls, owner only


class CalendarKeyError(RuntimeError):
    """The Calendar key is missing, expired or revoked; a person must renew it."""


@dataclass(frozen=True)
class CalendarSettings:
    """The host's private Calendar settings. Any missing part means "not connected"."""

    calendar_ids: Mapping[str, str]
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    redirect_uri: str | None = None  # where Google sends the president back after Connect (T-46)
    token_key: str | None = None  # optional host key for the stored tokens; else derived from the session secret

    @property
    def has_key(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    @property
    def can_connect(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)


def settings_from_env(values: Mapping[str, str]) -> CalendarSettings:
    return CalendarSettings(
        calendar_ids=calendar_ids_from_json(values.get("CLUBOPS_GOOGLE_CALENDAR_IDS_JSON", "")),
        client_id=values.get("CLUBOPS_CALENDAR_CLIENT_ID") or None,
        client_secret=values.get("CLUBOPS_CALENDAR_CLIENT_SECRET") or None,
        refresh_token=values.get("CLUBOPS_CALENDAR_REFRESH_TOKEN") or None,
        redirect_uri=values.get("CLUBOPS_CALENDAR_REDIRECT_URI") or None,
        token_key=values.get("CLUBOPS_CALENDAR_TOKEN_KEY") or None,
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


class ConnectError(RuntimeError):
    """Connecting Google Calendar failed; the message is safe to show the president."""


class CalendarService:
    def __init__(
        self,
        data_dir: Path,
        settings: CalendarSettings,
        *,
        transport: httpx.BaseTransport | None = None,
        session_secret: str = "",
    ) -> None:
        self.data_dir = data_dir
        self.settings = settings
        self.transport = transport
        self.queue = SyncQueue(data_dir / QUEUE_FILE)
        self.vault = ConnectionVault(data_dir, token_key(session_secret or "dev-only-secret", settings.token_key))
        self._lock = threading.Lock()  # one drain at a time: there is a single worker (README, J-23)
        self.problems: dict[str, str] = {}  # each club's last drain problem, shown until a drain works

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

    def enqueue_mail_deadlines(self, club_id: str, tasks: list[DeadlineTask], today: date, source_key: str) -> int:
        """Queue the deadlines of one clean trusted OSA e-mail, one task per role (D-138). The caller has already
        checked the mail (listed sender, no hidden instructions, not outdated); odd dates are held by the queue.
        Returns how many tasks were queued (F-316)."""
        if not tasks or not self.has_calendar(club_id):
            return 0
        result = self.queue.enqueue_deadlines(
            DeadlineTasksRequest(club_id=club_id, today=today, trusted=True, tasks=tasks), source_key=source_key
        )
        return len(result.items)

    # ------------------------------------------------------------ the key

    def _key_for(self, club_id: str) -> CalendarSettings:
        """The Google key a club's calls use: the one its president connected in the app, else the host's.
        A connected key that Google has ended is never swapped for the host's: the president must reconnect."""
        if self.vault.has(club_id):
            saved = None if self.vault.needs_reconnect(club_id) else self.vault.load(club_id)
            if saved is None:
                raise CalendarKeyError(RECONNECT_HINT)
            return replace(self.settings, refresh_token=saved)
        return self.settings

    def _access_token(self, club_id: str) -> str:
        key = self._key_for(club_id)
        try:
            return access_token(key, transport=self.transport)
        except CalendarKeyError:
            if self.vault.has(club_id):
                self.vault.mark_reconnect(club_id)
                raise CalendarKeyError(RECONNECT_HINT) from None
            raise

    # ----------------------------------------------------------- connecting

    def connection(self, club_id: str) -> dict[str, Any]:
        """Own-club connection state for the Calendar screen. No token, address or calendar id is ever included.
        ``state``: not_set_up (the host lacks the Google app or a calendar), not_connected, connected, reconnect."""
        waiting = self.vault.shares(club_id)
        base = {
            "can_connect": self.settings.can_connect and self.has_calendar(club_id),
            "access_changes_waiting": len(waiting),
        }
        if not self.has_calendar(club_id):
            return {**base, "state": "not_set_up", "source": None}
        if self.vault.has(club_id):
            state = "reconnect" if self.vault.needs_reconnect(club_id) else "connected"
            return {**base, "state": state, "source": "app"}
        if self.settings.has_key:
            return {**base, "state": "connected", "source": "host"}
        return {**base, "state": "not_set_up" if not base["can_connect"] else "not_connected", "source": None}

    def start_connect(self, club_id: str, member_id: str, now: datetime) -> str:
        """The Google address the president's browser should open. Needs the host's Google app and a club calendar."""
        if not (self.settings.can_connect and self.has_calendar(club_id)):
            raise ConnectError("Google Calendar is not set up on the host yet.")
        assert self.settings.client_id and self.settings.redirect_uri  # noqa: S101 (can_connect checked above)
        return authorization_url(
            self.settings.client_id, self.settings.redirect_uri, self.vault.begin(club_id, member_id, now)
        )

    def finish_connect(self, club_id: str, member_id: str, state: str, code: str, now: datetime) -> None:
        """Google sent the president back: check the proof, swap the code for a key, check the account and both
        permissions, then keep the key encrypted. Nothing is stored unless every check passes."""
        if not self.vault.consume(state, club_id, member_id, now):
            raise ConnectError("This connect link is not valid any more. Press Connect again.")
        if not (self.settings.can_connect and self.has_calendar(club_id)):
            raise ConnectError("Google Calendar is not set up on the host yet.")
        try:
            with httpx.Client(transport=self.transport, timeout=15) as client:
                reply = client.post(
                    TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self.settings.client_id,
                        "client_secret": self.settings.client_secret,
                        "redirect_uri": self.settings.redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                body = reply.json() if reply.status_code == 200 else {}
                refresh, access = body.get("refresh_token"), body.get("access_token")
                if not (isinstance(refresh, str) and refresh and isinstance(access, str) and access):
                    raise ConnectError("Google did not give access. Press Connect again and allow every permission.")
                if not scopes_ok(str(body.get("scope", ""))):
                    raise ConnectError("Both calendar permissions are needed. Press Connect again and allow both.")
                role = client.get(
                    CALENDAR_URL + quote(self.settings.calendar_ids[club_id], safe="") + "/acl",
                    params={"maxResults": 1},
                    headers={"Authorization": f"Bearer {access}"},
                )
        except (OSError, httpx.HTTPError, ValueError):
            raise ConnectError("Google could not be reached. Try again in a minute.") from None
        if role.status_code >= 500:
            raise ConnectError("Google could not be reached. Try again in a minute.")
        if role.status_code != 200:  # Google lists a calendar's sharing rules to its owner only
            raise ConnectError(WRONG_ACCOUNT)  # only the owner can share the calendar with the cabinet
        self.vault.save(club_id, refresh, member_id, now)
        self.problems.pop(club_id, None)

    def disconnect(self, club_id: str) -> None:
        """Forget the club's key and ask Google to cancel it. Queued items stay queued. Cancelling is best effort:
        the key is gone from here either way."""
        saved = self.vault.load(club_id)
        self.vault.delete(club_id)
        self.problems.pop(club_id, None)
        if saved:
            try:
                with httpx.Client(transport=self.transport, timeout=15) as client:
                    client.post(REVOKE_URL, data={"token": saved})
            except (OSError, httpx.HTTPError):
                pass

    # ------------------------------------------------- reader access (J-21)

    def share_with(self, club_id: str, email: str, *, grant: bool) -> None:
        """Remember that a cabinet member should (or no longer should) read the club calendar. Reader access only;
        the change is sent by the next drain, so a Google outage never blocks the cabinet list."""
        if self.has_calendar(club_id):
            self.vault.want_share(club_id, email, "grant" if grant else "revoke")

    def _share(self, club_id: str) -> str | None:
        wanted = self.vault.shares(club_id)
        if not wanted:
            return None
        try:
            sharing = GoogleCalendarSharing(self._access_token(club_id), transport=self.transport)
        except CalendarKeyError as exc:
            return str(exc)
        except (OSError, httpx.HTTPError):
            return "Google could not be reached. The calendar will retry."
        calendar_id = self.settings.calendar_ids[club_id]
        for email, action in wanted:
            try:
                (sharing.grant_reader if action == "grant" else sharing.revoke_reader)(calendar_id, email)
            except (SharingError, ValueError) as exc:
                self.vault.share_failed(club_id, email, str(exc))
            else:
                self.vault.share_done(club_id, email, action)
        return None

    # ---------------------------------------------------------------- drain

    def drain(self, club_id: str | None = None) -> str | None:
        """Send what is waiting, club by club, then apply waiting reader changes. Returns a short problem text,
        or ``None``. A failure leaves the work queued."""
        clubs = [club_id] if club_id else sorted({i.club_id for i in self.queue.pending()} | self._share_clubs())
        first: str | None = None
        for club in clubs:
            with self._lock:
                problem = self._drain_club(club) or self._share(club)
            if problem:
                self.problems[club] = problem
                first = first or problem
            else:
                self.problems.pop(club, None)
        return first

    def _share_clubs(self) -> set[str]:
        with closing(sqlite3.connect(self.vault.path)) as db:
            return {str(r[0]) for r in db.execute("SELECT DISTINCT club_id FROM sharing_pending")}

    def _drain_club(self, club_id: str) -> str | None:
        if not self.queue.pending(club_id):
            return None
        try:
            if not (self.vault.has(club_id) or self.settings.has_key):
                return "The Calendar key is not set on the host."
            token = self._access_token(club_id)
            sync = CalendarSync(GoogleCalendarGateway(token, transport=self.transport), self.settings.calendar_ids)
            self.queue.drain(sync, lambda c: cabinet_addresses(self.data_dir, c), club_id)
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
        connection = self.connection(club_id)
        return {
            "connected": connection["state"] == "connected",
            "waiting": len(rows),
            "problem": self.problems.get(club_id) or (errors[0] if errors else None),
        }
