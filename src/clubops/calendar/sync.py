"""Keep a club's Google calendar aligned with approved ClubOps items."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Protocol

import httpx
from pydantic import EmailStr, TypeAdapter, ValidationError

from clubops.contracts.calendar import CalendarItem, ItemKind, ItemOrigin, ItemStatus, Reminder
from clubops.contracts.common import CABINET_ROLES, Role

BEIRUT = "Asia/Beirut"
_EMAIL = TypeAdapter(EmailStr)


class CalendarGateway(Protocol):
    def put(self, calendar_id: str, event_id: str, body: dict[str, object]) -> None: ...
    def delete(self, calendar_id: str, event_id: str) -> None: ...


class SyncError(Exception):
    """Google is unavailable; the caller should retain a pending sync job."""


@dataclass(frozen=True)
class SyncResult:
    synced: bool
    missing_roles: tuple[Role, ...] = ()


def google_id(club_id: str, item_id: str, suffix: str = "") -> str:
    """Google permits base32hex ids; a stable hash also isolates clubs."""
    return "c" + hashlib.sha256(f"{club_id}/{item_id}/{suffix}".encode()).hexdigest()[:40]


def _notification_at(item: CalendarItem, reminder: Reminder) -> datetime:
    if reminder.before_days is not None:
        return datetime.combine(item.date - timedelta(days=reminder.before_days), time(8))
    if reminder.after_days is not None:
        return datetime.combine(item.date + timedelta(days=reminder.after_days), time(8))
    if reminder.on_day_at is None:
        raise ValueError("reminder has no notification time")
    return datetime.combine(item.date, reminder.on_day_at)


def _body(item: CalendarItem) -> dict[str, object]:
    body: dict[str, object] = {
        "summary": item.title,
        "description": item.link or "ClubOps task",
        "extendedProperties": {"private": {"clubops_item_id": item.item_id, "clubops_club_id": item.club_id}},
        "reminders": {"useDefault": False, "overrides": []},
    }
    if item.kind is ItemKind.EVENT:
        if item.start is None or item.end is None:
            raise ValueError("event times are required")
        body["start"] = {"dateTime": item.start.isoformat()}
        body["end"] = {"dateTime": item.end.isoformat()}
    else:
        body["start"] = {"date": item.date.isoformat()}
        body["end"] = {"date": (item.date + timedelta(days=1)).isoformat()}
    return body


def _reminder_body(item: CalendarItem, when: datetime) -> dict[str, object]:
    body: dict[str, object] = {
        "summary": f"Reminder: {item.title}",
        "description": item.link or "ClubOps reminder",
        "start": {"dateTime": when.isoformat(), "timeZone": BEIRUT},
        "end": {"dateTime": (when + timedelta(minutes=15)).isoformat(), "timeZone": BEIRUT},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 0}]},
        "extendedProperties": {"private": {"clubops_item_id": item.item_id, "clubops_club_id": item.club_id}},
    }
    return body


class CalendarSync:
    def __init__(
        self,
        gateway: CalendarGateway,
        calendars: Mapping[str, str],
        reminder_calendars: Mapping[str, Mapping[Role, str]] | None = None,
    ) -> None:
        self.gateway = gateway
        self.calendars = calendars
        self.reminder_calendars = reminder_calendars

    def sync(
        self,
        item: CalendarItem,
        *,
        approved: bool,
        role_emails: Mapping[Role, str],
        trusted_mail: bool = False,
    ) -> SyncResult:
        if not approved and not (trusted_mail and item.origin is ItemOrigin.MAIL and item.kind is ItemKind.TASK):
            raise ValueError("calendar sync requires an approved plan")
        if len(item.reminders) > 5:
            raise ValueError("at most five reminders are supported per item")
        if self.reminder_calendars is None:
            return self._sync_cabinet(item, role_emails)
        calendar_id = self.calendars[item.club_id]
        missing: tuple[Role, ...] = ()
        role_calendars = self.reminder_calendars[item.club_id]
        targets: set[str] = set()
        if item.status is ItemStatus.OPEN and item.reminders and item.owner_role == "all_cabinet":
            targets = set(role_calendars.values())
            if not targets:
                raise ValueError("cabinet reminder calendars are not configured")
        elif item.status is ItemStatus.OPEN and item.reminders:
            role = item.owner_role
            if role == "all_cabinet":
                raise ValueError("cabinet reminder calendars are not configured")
            if role not in role_emails or role not in role_calendars:
                missing = (role,)
                role = Role.PRESIDENT
            if role not in role_calendars:
                raise ValueError("president reminder calendar is not configured")
            targets = {role_calendars[role]}
        primary_id = google_id(item.club_id, item.item_id)
        try:
            if item.status is ItemStatus.CANCELLED:
                self.gateway.delete(calendar_id, primary_id)
            else:
                self.gateway.put(calendar_id, primary_id, _body(item))
            for index in range(5):
                reminder_id = google_id(item.club_id, item.item_id, f"reminder-{index}")
                if item.status is ItemStatus.OPEN and index < len(item.reminders):
                    when = _notification_at(item, item.reminders[index])
                    for target in targets:
                        self.gateway.put(target, reminder_id, _reminder_body(item, when))
                active_targets = targets if item.status is ItemStatus.OPEN and index < len(item.reminders) else set()
                for old_calendar in {calendar_id, *role_calendars.values()} - active_targets:
                    self.gateway.delete(old_calendar, reminder_id)
        except (OSError, httpx.HTTPError) as exc:
            raise SyncError("calendar not synced; retry later") from exc
        return SyncResult(synced=True, missing_roles=missing)

    def _sync_cabinet(self, item: CalendarItem, role_emails: Mapping[Role, str]) -> SyncResult:
        """One shared calendar; recipients come only from the backend's current cabinet directory."""
        if item.owner_role != "all_cabinet" and item.owner_role not in CABINET_ROLES:
            raise ValueError("calendar tasks go to cabinet roles only")
        missing: tuple[Role, ...] = ()
        recipients: set[str] = set()
        if item.status is ItemStatus.OPEN:
            roles = CABINET_ROLES if item.owner_role == "all_cabinet" else {item.owner_role}
            for role in sorted(roles):
                address = role_emails.get(role)
                if not address:
                    missing += (role,)
                    address = role_emails.get(Role.PRESIDENT)
                if not address:
                    raise ValueError("president cabinet address is not configured")
                try:
                    recipients.add(str(_EMAIL.validate_python(address)))
                except ValidationError:
                    raise ValueError("invalid cabinet address configuration") from None
        audience: dict[str, object] = {
            "attendees": [{"email": address} for address in sorted(recipients)],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": False,
        }
        calendar_id = self.calendars[item.club_id]
        primary_id = google_id(item.club_id, item.item_id)
        try:
            if item.status is ItemStatus.CANCELLED:
                self.gateway.delete(calendar_id, primary_id)
            else:
                self.gateway.put(calendar_id, primary_id, {**_body(item), **audience})
            for index in range(5):
                reminder_id = google_id(item.club_id, item.item_id, f"reminder-{index}")
                if item.status is ItemStatus.OPEN and index < len(item.reminders):
                    body = _reminder_body(item, _notification_at(item, item.reminders[index]))
                    self.gateway.put(calendar_id, reminder_id, {**body, **audience})
                else:
                    self.gateway.delete(calendar_id, reminder_id)
        except (OSError, httpx.HTTPError) as exc:
            raise SyncError("calendar not synced; retry later") from exc
        return SyncResult(synced=True, missing_roles=missing)


class GoogleCalendarGateway:
    """HTTP adapter; caller supplies a short-lived OAuth token and a club calendar ID."""

    def __init__(self, access_token: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self.access_token = access_token
        self.transport = transport

    def _request(self, method: str, calendar_id: str, event_id: str, body: dict[str, object] | None) -> None:
        from urllib.parse import quote

        url = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id, safe='')}/events"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        with httpx.Client(transport=self.transport, timeout=15) as client:
            if method == "DELETE":
                response = client.delete(f"{url}/{event_id}", headers=headers, params={"sendUpdates": "all"})
                if response.status_code not in (204, 404, 410):
                    response.raise_for_status()
                return
            response = client.put(f"{url}/{event_id}", headers=headers, json=body, params={"sendUpdates": "all"})
            if response.status_code == 404:
                response = client.post(
                    url, headers=headers, json={"id": event_id, **(body or {})}, params={"sendUpdates": "all"}
                )
                if response.status_code == 409:
                    response = client.put(
                        f"{url}/{event_id}", headers=headers, json=body, params={"sendUpdates": "all"}
                    )
            response.raise_for_status()

    def put(self, calendar_id: str, event_id: str, body: dict[str, object]) -> None:
        self._request("PUT", calendar_id, event_id, body)

    def delete(self, calendar_id: str, event_id: str) -> None:
        self._request("DELETE", calendar_id, event_id, None)
