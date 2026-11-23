"""Where know-how is kept. The rules (verified writes, versions, history) live in ``KnowHowStore``;
a backend only stores and finds things, so memory and SQLite behave identically (ADR 0004, D-35).

- ``MemoryBackend``: for tests and quick runs.
- ``SqliteBackend``: one SQLite file, with full-text search (FTS5) over the latest version of each item.
- ``SplitBackend``: the real layout (D-23): one shared General file for AUB-wide items and one file per
  club for its own items and its review queue. A club's file never contains another club's know-how.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path
from typing import Protocol

from clubops.contracts.common import ItemId
from clubops.contracts.knowhow import KnowHowItem, KnowHowProposal, Scope

_WORD = re.compile(r"\w+", re.UNICODE)


def _terms(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _searchable(item: KnowHowItem) -> str:
    return " ".join([item.title, item.statement, *item.tags])


class Backend(Protocol):
    def versions(self, item_id: ItemId) -> list[KnowHowItem]: ...
    def latest_all(self) -> list[KnowHowItem]: ...
    def has(self, item_id: ItemId) -> bool: ...
    def append(self, item: KnowHowItem) -> None: ...
    def replace_latest(self, item: KnowHowItem) -> None: ...
    def pending_all(self) -> dict[str, KnowHowProposal]: ...
    def pending_put(self, proposal: KnowHowProposal) -> None: ...
    def pending_delete(self, proposal_id: str) -> None: ...
    def rejected_all(self) -> set[str]: ...
    def rejected_add(self, proposal_id: str) -> None: ...
    def rejected_delete(self, proposal_id: str) -> None: ...
    def search(self, text: str, limit: int) -> list[tuple[ItemId, float]]: ...
    def transaction(self) -> AbstractContextManager[None]: ...
    def close(self) -> None: ...


# --------------------------------------------------------------------- memory


class MemoryBackend:
    def __init__(self) -> None:
        self._versions: dict[ItemId, list[KnowHowItem]] = {}
        self._pending: dict[str, KnowHowProposal] = {}
        self._rejected: set[str] = set()

    def versions(self, item_id: ItemId) -> list[KnowHowItem]:
        return list(self._versions.get(item_id, []))

    def latest_all(self) -> list[KnowHowItem]:
        return [v[-1] for v in self._versions.values()]

    def has(self, item_id: ItemId) -> bool:
        return item_id in self._versions

    def append(self, item: KnowHowItem) -> None:
        self._versions.setdefault(item.item_id, []).append(item)

    def replace_latest(self, item: KnowHowItem) -> None:
        self._versions[item.item_id][-1] = item

    def pending_all(self) -> dict[str, KnowHowProposal]:
        return dict(self._pending)

    def pending_put(self, proposal: KnowHowProposal) -> None:
        self._pending[proposal.proposal_id] = proposal

    def pending_delete(self, proposal_id: str) -> None:
        self._pending.pop(proposal_id, None)

    def rejected_all(self) -> set[str]:
        return set(self._rejected)

    def rejected_add(self, proposal_id: str) -> None:
        self._rejected.add(proposal_id)

    def rejected_delete(self, proposal_id: str) -> None:
        self._rejected.discard(proposal_id)

    def search(self, text: str, limit: int) -> list[tuple[ItemId, float]]:
        wanted = set(_terms(text))
        scored = []
        for item in self.latest_all():
            words = _terms(_searchable(item))
            score = float(sum(words.count(t) for t in wanted))
            if score:
                scored.append((item.item_id, score))
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:limit]

    def transaction(self) -> AbstractContextManager[None]:
        return nullcontext()

    def close(self) -> None:
        return None


# --------------------------------------------------------------------- sqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS item_versions (
    item_id   TEXT NOT NULL,
    version   INTEGER NOT NULL,
    scope     TEXT NOT NULL,
    club_id   TEXT,
    status    TEXT NOT NULL,
    body      TEXT NOT NULL,
    PRIMARY KEY (item_id, version)
);
CREATE TABLE IF NOT EXISTS pending (
    proposal_id TEXT PRIMARY KEY,
    body        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rejected (
    proposal_id TEXT PRIMARY KEY
);
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(item_id UNINDEXED, content, tokenize = 'unicode61');
"""


class SqliteBackend:
    def __init__(self, path: Path | str) -> None:
        if isinstance(path, Path):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), isolation_level=None)  # explicit transactions below
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(_SCHEMA)
        self._depth = 0

    def close(self) -> None:
        self._db.close()

    def versions(self, item_id: ItemId) -> list[KnowHowItem]:
        rows = self._db.execute(
            "SELECT body FROM item_versions WHERE item_id = ? ORDER BY version", (item_id,)
        ).fetchall()
        return [KnowHowItem.model_validate_json(r[0]) for r in rows]

    def latest_all(self) -> list[KnowHowItem]:
        rows = self._db.execute(
            """SELECT v.body FROM item_versions v
               JOIN (SELECT item_id, MAX(version) AS version FROM item_versions GROUP BY item_id) m
               USING (item_id, version) ORDER BY v.item_id"""
        ).fetchall()
        return [KnowHowItem.model_validate_json(r[0]) for r in rows]

    def has(self, item_id: ItemId) -> bool:
        row = self._db.execute("SELECT 1 FROM item_versions WHERE item_id = ? LIMIT 1", (item_id,)).fetchone()
        return row is not None

    def _index(self, item: KnowHowItem) -> None:
        self._db.execute("DELETE FROM items_fts WHERE item_id = ?", (item.item_id,))
        self._db.execute("INSERT INTO items_fts (item_id, content) VALUES (?, ?)", (item.item_id, _searchable(item)))

    def append(self, item: KnowHowItem) -> None:
        with self.transaction():
            self._db.execute(
                "INSERT INTO item_versions (item_id, version, scope, club_id, status, body) VALUES (?, ?, ?, ?, ?, ?)",
                (item.item_id, item.version, item.scope.value, item.club_id, item.status.value, item.model_dump_json()),
            )
            self._index(item)

    def replace_latest(self, item: KnowHowItem) -> None:
        with self.transaction():
            self._db.execute(
                """UPDATE item_versions SET status = ?, body = ?
                   WHERE item_id = ? AND version = (SELECT MAX(version) FROM item_versions WHERE item_id = ?)""",
                (item.status.value, item.model_dump_json(), item.item_id, item.item_id),
            )
            self._index(item)

    def pending_all(self) -> dict[str, KnowHowProposal]:
        rows = self._db.execute("SELECT proposal_id, body FROM pending ORDER BY proposal_id").fetchall()
        return {r[0]: KnowHowProposal.model_validate_json(r[1]) for r in rows}

    def pending_put(self, proposal: KnowHowProposal) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO pending (proposal_id, body) VALUES (?, ?)",
            (proposal.proposal_id, proposal.model_dump_json()),
        )

    def pending_delete(self, proposal_id: str) -> None:
        self._db.execute("DELETE FROM pending WHERE proposal_id = ?", (proposal_id,))

    def rejected_all(self) -> set[str]:
        return {r[0] for r in self._db.execute("SELECT proposal_id FROM rejected").fetchall()}

    def rejected_add(self, proposal_id: str) -> None:
        self._db.execute("INSERT OR IGNORE INTO rejected (proposal_id) VALUES (?)", (proposal_id,))

    def rejected_delete(self, proposal_id: str) -> None:
        self._db.execute("DELETE FROM rejected WHERE proposal_id = ?", (proposal_id,))

    def search(self, text: str, limit: int) -> list[tuple[ItemId, float]]:
        terms = _terms(text)
        if not terms:
            return []
        # Each word quoted, joined with OR: user text can never inject FTS5 query syntax.
        query = " OR ".join('"' + t.replace('"', "") + '"' for t in terms)
        rows = self._db.execute(
            """SELECT item_id, bm25(items_fts) FROM items_fts WHERE items_fts MATCH ?
               ORDER BY bm25(items_fts), item_id LIMIT ?""",
            (query, limit),
        ).fetchall()
        return [(r[0], -float(r[1])) for r in rows]  # bm25: lower is better; flip so higher is better

    @contextmanager
    def _tx(self) -> Iterator[None]:
        outer = self._depth == 0
        if outer:
            self._db.execute("BEGIN")
        self._depth += 1
        try:
            yield
        except BaseException:
            self._depth -= 1
            if outer:
                self._db.execute("ROLLBACK")
            raise
        self._depth -= 1
        if outer:
            self._db.execute("COMMIT")

    def transaction(self) -> AbstractContextManager[None]:
        return self._tx()


# ---------------------------------------------------------------------- split


class SplitBackend:
    """General (AUB-wide) items in one backend, the club's items and review queue in another."""

    def __init__(self, general: Backend, club: Backend) -> None:
        self.general = general
        self.club = club

    def _home(self, item: KnowHowItem) -> Backend:
        if self.club.has(item.item_id):
            return self.club
        if self.general.has(item.item_id):
            return self.general
        return self.general if item.scope is Scope.AUB else self.club

    def versions(self, item_id: ItemId) -> list[KnowHowItem]:
        return self.club.versions(item_id) or self.general.versions(item_id)

    def latest_all(self) -> list[KnowHowItem]:
        return [*self.general.latest_all(), *self.club.latest_all()]

    def has(self, item_id: ItemId) -> bool:
        return self.club.has(item_id) or self.general.has(item_id)

    def append(self, item: KnowHowItem) -> None:
        self._home(item).append(item)

    def replace_latest(self, item: KnowHowItem) -> None:
        self._home(item).replace_latest(item)

    def pending_all(self) -> dict[str, KnowHowProposal]:
        return self.club.pending_all()

    def pending_put(self, proposal: KnowHowProposal) -> None:
        self.club.pending_put(proposal)

    def pending_delete(self, proposal_id: str) -> None:
        self.club.pending_delete(proposal_id)

    def rejected_all(self) -> set[str]:
        return self.club.rejected_all()

    def rejected_add(self, proposal_id: str) -> None:
        self.club.rejected_add(proposal_id)

    def rejected_delete(self, proposal_id: str) -> None:
        self.club.rejected_delete(proposal_id)

    def search(self, text: str, limit: int) -> list[tuple[ItemId, float]]:
        merged = [*self.general.search(text, limit), *self.club.search(text, limit)]
        merged.sort(key=lambda pair: (-pair[1], pair[0]))
        return merged[:limit]

    @contextmanager
    def _tx(self) -> Iterator[None]:
        with self.general.transaction(), self.club.transaction():
            yield

    def transaction(self) -> AbstractContextManager[None]:
        return self._tx()

    def close(self) -> None:
        self.general.close()
        self.club.close()


def open_club_store_backend(data_dir: Path, club_id: str) -> SplitBackend:
    """The production layout: ``<data_dir>/general.db`` + ``<data_dir>/clubs/<club_id>.db``."""
    return SplitBackend(
        general=SqliteBackend(data_dir / "general.db"),
        club=SqliteBackend(data_dir / "clubs" / f"{club_id}.db"),
    )
