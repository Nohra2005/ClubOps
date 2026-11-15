"""Term-only facts expire on their end date and stay as history; a president can restore one (D-115, F-215).
Synthetic data only, no model call."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from clubops.api.app import ApiConfig, create_app
from clubops.api.security import MemberStore
from clubops.capabilities.runner import CapabilityError
from clubops.contracts.common import Role
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore
from tests.factories import CLUB, NOW, actor, item, verified
from tests.test_learning import HEADERS

ENDED = NOW.date() - timedelta(days=1)


def _expired_store() -> KnowHowStore:
    store = KnowHowStore()
    store.backend.append(verified(item("kh-term-room", valid_to=ENDED)))
    return store


def test_an_expired_fact_is_not_used_but_is_kept() -> None:
    store = _expired_store()
    assert store.current(CLUB, NOW.date()) == []
    assert store.latest("kh-term-room") is not None


def test_restore_gives_a_new_version_the_planner_uses_again() -> None:
    store = _expired_store()
    restored = store.restore("kh-term-room", actor(Role.PRESIDENT), NOW, date(2026, 12, 31))
    assert restored.version == 2 and restored.valid_to == date(2026, 12, 31)
    assert [i.item_id for i in store.current(CLUB, NOW.date())] == ["kh-term-room"]
    assert len(store.history("kh-term-room")) == 2


@pytest.mark.parametrize(
    "stored, new_end",
    [
        (verified(item("kh-term-room", valid_to=NOW.date() + timedelta(days=5))), None),  # not expired yet
        (verified(item("kh-term-room", valid_to=ENDED)), ENDED),  # new end already past
        (verified(item("kh-term-room", club_id="chess-club", valid_to=ENDED)), None),  # another club's fact
    ],
)
def test_restore_refuses_wrong_cases(stored: object, new_end: date | None) -> None:
    store = KnowHowStore()
    store.backend.append(stored)  # type: ignore[arg-type]
    with pytest.raises(CapabilityError):
        store.restore("kh-term-room", actor(Role.PRESIDENT), NOW, new_end)
    assert len(store.history("kh-term-room")) == 1


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    people = MemberStore(tmp_path)
    people.add(CLUB, "Test President", "tp01@mail.aub.edu", Role.PRESIDENT)
    people.add(CLUB, "Test Treasurer", "tt02@mail.aub.edu", Role.TREASURER)
    people.close()
    store = KnowHowStore(open_club_store_backend(tmp_path, CLUB))
    store.backend.append(verified(item("kh-term-room", valid_to=ENDED)))
    config = ApiConfig(data_dir=tmp_path, session_secret="t", dev_login=True, cookie_secure=False)  # noqa: S106
    with TestClient(create_app(config, clock=lambda: NOW)) as c:
        yield c


def test_only_the_president_restores_through_the_app(client: TestClient) -> None:
    client.post("/api/auth/dev", json={"email": "tt02@mail.aub.edu"}, headers=HEADERS)
    assert client.post("/api/knowledge/kh-term-room/restore", json={}, headers=HEADERS).status_code == 403
    client.post("/api/auth/dev", json={"email": "tp01@mail.aub.edu"}, headers=HEADERS)
    response = client.post("/api/knowledge/kh-term-room/restore", json={"valid_to": "2026-12-31"}, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "current"
