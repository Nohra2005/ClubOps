"""Access to the ClubOps Gmail inbox: turn the saved refresh token into a short-lived access token, and
list who may forward mail for each club. No model call happens here (T-47, D-122)."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - a public endpoint, not a secret
RENEW_HINT = (
    "Gmail key expired or was revoked. In Testing mode Google cancels it every 7 days: "
    "get a new refresh token in the OAuth Playground and replace CLUBOPS_GMAIL_REFRESH_TOKEN."
)


class GmailKeyError(RuntimeError):
    """The saved Gmail key is missing, expired or revoked; a person must renew it."""


def access_token(
    client_id: str | None,
    client_secret: str | None,
    refresh_token: str | None,
    *,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Exchange the refresh token for an access token. Expired or revoked keys raise GmailKeyError."""
    if not (client_id and client_secret and refresh_token):
        raise GmailKeyError(
            "Gmail is not set up: CLUBOPS_GMAIL_CLIENT_ID, CLUBOPS_GMAIL_CLIENT_SECRET and "
            "CLUBOPS_GMAIL_REFRESH_TOKEN must all be in .env."
        )
    with httpx.Client(transport=transport, timeout=15) as client:
        response = client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code in (400, 401):
        try:
            error = str(response.json().get("error", ""))
        except ValueError:
            error = ""
        if error in ("invalid_grant", "unauthorized_client", "invalid_client"):
            raise GmailKeyError(RENEW_HINT if error == "invalid_grant" else f"Gmail client rejected ({error}).")
    response.raise_for_status()
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise GmailKeyError("Google returned no access token.")
    return token


def parse_extra_senders(value: str | None) -> dict[str, set[str]]:
    """``club:a@x,b@y;club2:c@z`` -> extra forwarding addresses per club (private .env only, until J-22)."""
    result: dict[str, set[str]] = {}
    for chunk in (value or "").split(";"):
        club, sep, addresses = chunk.partition(":")
        club = club.strip().lower()
        if not sep or not club:
            continue
        found = {a.strip().casefold() for a in addresses.split(",") if "@" in a}
        if found:
            result.setdefault(club, set()).update(found)
    return result


def cabinet_senders(data_dir: Path, extra: Mapping[str, set[str]] | None = None) -> dict[str, set[str]]:
    """Every club's cabinet e-mails (members and advisers excluded), plus any extra forwarding addresses."""
    senders: dict[str, set[str]] = {}
    database = data_dir / "general.db"
    if database.is_file():
        with closing(sqlite3.connect(database)) as db:
            try:
                rows = db.execute(
                    "SELECT club_id, email FROM members WHERE role NOT IN ('member', 'adviser')"
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        for club_id, email in rows:
            senders.setdefault(str(club_id), set()).add(str(email).casefold())
    for club_id, addresses in (extra or {}).items():
        senders.setdefault(club_id, set()).update(a.casefold() for a in addresses)
    return senders
