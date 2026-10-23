"""What only the SQLite layout adds: data survives a restart, clubs stay in separate files,
full-text search, and all-or-nothing writes. Synthetic data only."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from clubops.contracts.common import Role
from clubops.contracts.knowhow import VerifyDecision, VerifyRequest
from clubops.knowhow.backends import MemoryBackend, SqliteBackend, open_club_store_backend
from clubops.knowhow.store import KnowHowStore
from tests.factories import CLUB, NOW, TODAY, actor, item, proposal, rule


@pytest.fixture(autouse=True)
def _close_stores(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Close every SQLite connection a test opens, so none is left dangling."""
    opened: list[SqliteBackend] = []
    original = SqliteBackend.__init__

    def tracking(self: SqliteBackend, path: Path | str) -> None:
        original(self, path)
        opened.append(self)

    monkeypatch.setattr(SqliteBackend, "__init__", tracking)
    yield
    for backend in opened:
        backend.close()


def accept(store: KnowHowStore, prop, who=None) -> None:  # type: ignore[no-untyped-def]
    store.submit(prop)
    store.verify(VerifyRequest(proposal=prop, decision=VerifyDecision.ACCEPT), who or actor(), NOW)


def test_data_survives_a_restart(tmp_path: Path) -> None:
    store = KnowHowStore(open_club_store_backend(tmp_path, CLUB))
    accept(store, proposal())
    store.submit(proposal(item("kh-other"), pid="p-waiting"))

    reopened = KnowHowStore(open_club_store_backend(tmp_path, CLUB))
    assert [i.item_id for i in reopened.current(CLUB, TODAY)] == ["kh-book-green-field"]
    assert list(reopened.pending) == ["p-waiting"]


def test_aub_rules_go_to_the_shared_file_and_club_tips_to_the_clubs_file(tmp_path: Path) -> None:
    store = KnowHowStore(open_club_store_backend(tmp_path, CLUB))
    accept(store, proposal())  # club tip
    accept(store, proposal(rule(), pid="p-rule"), who=actor(Role.PRESIDENT))  # AUB-wide rule

    def ids(path: Path) -> set[str]:
        with closing(sqlite3.connect(path)) as db:
            return {r[0] for r in db.execute("SELECT item_id FROM item_versions")}

    assert ids(tmp_path / "general.db") == {"kh-rule-guests"}
    assert ids(tmp_path / "clubs" / f"{CLUB}.db") == {"kh-book-green-field"}


def test_another_club_sees_the_shared_rules_but_not_our_tips(tmp_path: Path) -> None:
    ours = KnowHowStore(open_club_store_backend(tmp_path, CLUB))
    accept(ours, proposal())
    accept(ours, proposal(rule(), pid="p-rule"), who=actor(Role.PRESIDENT))

    theirs = KnowHowStore(open_club_store_backend(tmp_path, "asme"))
    assert [i.item_id for i in theirs.current("asme", TODAY)] == ["kh-rule-guests"]
    assert not (tmp_path / "clubs" / "asme.db").read_bytes().count(b"kh-book-green-field")


@pytest.mark.parametrize("make", ["memory", "sqlite"])
def test_search_finds_the_best_match_first(tmp_path: Path, make: str) -> None:
    backend = MemoryBackend() if make == "memory" else SqliteBackend(tmp_path / "s.db")
    store = KnowHowStore(backend)
    accept(store, proposal(item("kh-gate", title="CHSC gate opening time", statement="The CHSC gate opens at 7 AM.")))
    beach = item("kh-beach", title="AUB Beach hours", statement="AUB Beach closes at 6:30 PM.")
    accept(store, proposal(beach, pid="p-2"))

    found = store.search(CLUB, "when does the gate open")
    assert [i.item_id for i in found][:1] == ["kh-gate"]
    assert store.search(CLUB, "") == []


def test_search_ignores_query_syntax_in_user_text(tmp_path: Path) -> None:
    store = KnowHowStore(SqliteBackend(tmp_path / "s.db"))
    accept(store, proposal(item("kh-gate", title="CHSC gate", statement="Opens at 7 AM.")))
    # Quotes, operators and column filters typed by a user must not break or steer the search.
    assert [i.item_id for i in store.search(CLUB, 'gate" OR content:* NEAR(')] == ["kh-gate"]


def test_search_hides_other_clubs_and_unapproved_items(tmp_path: Path) -> None:
    store = KnowHowStore(SqliteBackend(tmp_path / "s.db"))
    accept(store, proposal(item("kh-ours", statement="Green Field booking tips.")))
    accept(
        store,
        proposal(item("kh-theirs", club_id="asme", statement="Green Field booking for ASME."), pid="p-2"),
        who=actor(club="asme"),
    )
    store.submit(proposal(item("kh-waiting", statement="Green Field booking, not approved yet."), pid="p-3"))

    assert [i.item_id for i in store.search(CLUB, "green field booking")] == ["kh-ours"]


def test_a_failed_write_leaves_nothing_half_done(tmp_path: Path) -> None:
    backend = SqliteBackend(tmp_path / "s.db")
    with pytest.raises(RuntimeError), backend.transaction():
        backend.append(item())
        raise RuntimeError("crash in the middle of a write")
    assert backend.latest_all() == []
