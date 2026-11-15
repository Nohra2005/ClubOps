"""Calendar sharing changes are limited to named cabinet readers."""

import json

import httpx
import pytest

from clubops.calendar.sharing import GoogleCalendarSharing, SharingError


def test_grant_is_idempotent_and_revoke_removes_only_named_reader() -> None:
    rules: dict[str, str] = {}
    calls: list[tuple[str, str]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/acl"):
            assert request.method == "POST"
            body = json.loads(request.content)
            assert body == {"role": "reader", "scope": {"type": "user", "value": "joey@example.test"}}
            rules["joey@example.test"] = "reader"
            return httpx.Response(200, json=body)
        if request.method == "GET":
            return (
                httpx.Response(200, json={"role": rules["joey@example.test"]})
                if "joey@example.test" in rules
                else httpx.Response(404)
            )
        rules.pop("joey@example.test", None)
        return httpx.Response(204)

    sharing = GoogleCalendarSharing("synthetic-token", transport=httpx.MockTransport(respond))
    sharing.grant_reader("club@example.test", "Joey@Example.test")
    sharing.grant_reader("club@example.test", "joey@example.test")
    sharing.revoke_reader("club@example.test", "joey@example.test")
    sharing.revoke_reader("club@example.test", "joey@example.test")
    assert [method for method, _ in calls].count("POST") == 1
    assert [method for method, _ in calls].count("DELETE") == 1
    assert all("club@example.test" in path for _, path in calls)
    assert rules == {}


def test_existing_writer_is_preserved_and_google_failure_is_reported() -> None:
    def writer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"role": "writer"})

    sharing = GoogleCalendarSharing("synthetic-token", transport=httpx.MockTransport(writer))
    with pytest.raises(SharingError, match="review it manually"):
        sharing.revoke_reader("club", "member@example.test")
    with pytest.raises(SharingError, match="review it manually"):
        sharing.grant_reader("club", "member@example.test")

    failed = GoogleCalendarSharing("synthetic-token", transport=httpx.MockTransport(lambda _: httpx.Response(401)))
    with pytest.raises(SharingError, match="authorization"):
        failed.grant_reader("club", "member@example.test")
