"""Read forwarded mail from Gmail; never reply or trigger AI during polling."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

import httpx

from clubops.inbox.capture import PendingInbox, capture_email


class MailGateway(Protocol):
    def list_ids(self) -> list[str]: ...
    def get_raw(self, message_id: str) -> bytes: ...


class GmailGateway:
    def __init__(self, access_token: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self.access_token = access_token
        self.transport = transport

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, object]:
        with httpx.Client(transport=self.transport, timeout=15) as client:
            response = client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/{path}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params,
            )
            response.raise_for_status()
            value = response.json()
        if not isinstance(value, dict):
            raise ValueError("unexpected Gmail response")
        return value

    def list_ids(self) -> list[str]:
        ids: list[str] = []
        page: str | None = None
        while True:
            params = {"maxResults": "100", "labelIds": "INBOX"}
            if page is not None:
                params["pageToken"] = page
            response = self._get("messages", params)
            messages = response.get("messages") or []
            if not isinstance(messages, list):
                raise ValueError("unexpected Gmail messages list")
            ids.extend(str(message["id"]) for message in messages if isinstance(message, dict) and "id" in message)
            next_page = response.get("nextPageToken")
            if not isinstance(next_page, str) or not next_page:
                return ids
            page = next_page

    def get_raw(self, message_id: str) -> bytes:
        response = self._get(f"messages/{message_id}", {"format": "raw"})
        raw = response.get("raw")
        if not isinstance(raw, str):
            raise ValueError("Gmail message has no raw MIME content")
        return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def fetch_into_queue(
    gateway: MailGateway,
    queue: PendingInbox,
    cabinet_senders: Mapping[str, set[str]],
    received_at: datetime,
) -> int:
    """Store authorized mail for an explicit human capture click; duplicates stay single."""
    added = 0
    for message_id in gateway.list_ids():
        request = capture_email(gateway.get_raw(message_id), message_id, cabinet_senders, received_at)
        if request is not None and queue.enqueue(message_id, request):
            added += 1
    return added
