"""Gmail key exchange and the forwarding-sender list (T-47, F-207, F-208). Synthetic data, no network."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import httpx
import pytest

from clubops.gmail_access import GmailKeyError, access_token, cabinet_senders, parse_extra_senders


def _transport(status: int, body: dict[str, str]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "oauth2.googleapis.com"
        assert b"grant_type=refresh_token" in request.content
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def test_refresh_token_becomes_access_token() -> None:
    token = access_token("id", "secret", "refresh", transport=_transport(200, {"access_token": "ya29.synthetic"}))
    assert token == "ya29.synthetic"  # noqa: S105 - synthetic test value


def test_expired_key_says_how_to_renew() -> None:
    with pytest.raises(GmailKeyError, match="every 7 days"):
        access_token("id", "secret", "old", transport=_transport(400, {"error": "invalid_grant"}))


def test_missing_settings_are_reported_not_sent() -> None:
    with pytest.raises(GmailKeyError, match="not set up"):
        access_token("id", None, "refresh", transport=_transport(200, {"access_token": "never"}))


def test_extra_senders_parse_per_club() -> None:
    parsed = parse_extra_senders("running-club: A@Example.org , b@example.org; asme:c@example.org; broken; x:")
    assert parsed == {"running-club": {"a@example.org", "b@example.org"}, "asme": {"c@example.org"}}


def test_cabinet_senders_exclude_members_and_advisers(tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "general.db") as db:
        db.execute("CREATE TABLE members (member_id, club_id, name, email, role)")
        db.executemany(
            "INSERT INTO members VALUES (?, ?, ?, ?, ?)",
            [
                ("m1", "demo-club", "P", "president@example.org", "president"),
                ("m2", "demo-club", "M", "member@example.org", "member"),
                ("m3", "demo-club", "A", "adviser@example.org", "adviser"),
            ],
        )
    senders = cabinet_senders(tmp_path, {"demo-club": {"Forward@Example.org"}})
    assert senders == {"demo-club": {"president@example.org", "forward@example.org"}}


def test_no_member_database_means_only_extra_senders(tmp_path: Path) -> None:
    assert cabinet_senders(tmp_path, {"demo-club": {"x@example.org"}}) == {"demo-club": {"x@example.org"}}
