"""Grant cabinet members read access to a club's shared Google calendar."""

from __future__ import annotations

from urllib.parse import quote

import httpx


class SharingError(Exception):
    """Google could not apply a calendar access change; retry after reconnecting."""


class GoogleCalendarSharing:
    """Only manage individual reader rules; never change public or owner access."""

    def __init__(self, access_token: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self.access_token = access_token
        self.transport = transport

    def _url(self, calendar_id: str, email: str | None = None) -> str:
        base = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id, safe='')}/acl"
        return base if email is None else f"{base}/{quote('user:' + email.lower(), safe='')}"

    def grant_reader(self, calendar_id: str, email: str) -> None:
        """Give a cabinet member read access; a repeated call is safe."""
        address = email.strip().lower()
        if not calendar_id or not address or "@" not in address:
            raise ValueError("calendar ID and member email are required")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        body = {"role": "reader", "scope": {"type": "user", "value": address}}
        try:
            with httpx.Client(transport=self.transport, timeout=15) as client:
                existing = client.get(self._url(calendar_id, address), headers=headers)
                if existing.status_code == 404:
                    response = client.post(self._url(calendar_id), headers=headers, json=body)
                    if response.status_code == 409:
                        response = client.get(self._url(calendar_id, address), headers=headers)
                else:
                    response = existing
                response.raise_for_status()
                if response.json().get("role") != "reader":
                    raise SharingError("existing calendar access is not reader; review it manually")
        except (OSError, httpx.HTTPError, ValueError) as exc:
            raise SharingError("calendar sharing failed; retry after checking authorization") from exc

    def revoke_reader(self, calendar_id: str, email: str) -> None:
        """Remove only a member's individual reader rule, if present."""
        address = email.strip().lower()
        if not calendar_id or not address or "@" not in address:
            raise ValueError("calendar ID and member email are required")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            with httpx.Client(transport=self.transport, timeout=15) as client:
                existing = client.get(self._url(calendar_id, address), headers=headers)
                if existing.status_code == 404:
                    return
                existing.raise_for_status()
                if existing.json().get("role") != "reader":
                    raise SharingError("existing calendar access is not reader; review it manually")
                response = client.delete(self._url(calendar_id, address), headers=headers)
                if response.status_code not in (204, 404):
                    response.raise_for_status()
        except (OSError, httpx.HTTPError, ValueError) as exc:
            raise SharingError("calendar sharing failed; retry after checking authorization") from exc
