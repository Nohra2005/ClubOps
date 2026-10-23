"""Contacts (D-10), assets (D-12) and event history (D-21), stored next to the know-how.

Same layout as the know-how store (D-23): AUB-wide entries (``club_id is None``, e.g. OSA offices,
official forms) live in the shared ``general.db``; a club's own entries live in its own file.
A directory opened for one club refuses to write another club's entries.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from clubops.capabilities.runner import CapabilityError
from clubops.contracts.common import ClubId, ErrorCode, EventId
from clubops.contracts.directory import Asset, Contact
from clubops.contracts.event import EventRecord

M = TypeVar("M", bound=BaseModel)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (id TEXT PRIMARY KEY, club_id TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assets   (id TEXT PRIMARY KEY, club_id TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events   (id TEXT PRIMARY KEY, club_id TEXT NOT NULL, on_date TEXT NOT NULL,
                                     body TEXT NOT NULL);
"""


def _open(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path))
    db.executescript(_SCHEMA)
    return db


class Directory:
    def __init__(self, data_dir: Path, club_id: ClubId) -> None:
        self.club_id = club_id
        self._general = _open(data_dir / "general.db")
        self._club = _open(data_dir / "clubs" / f"{club_id}.db")

    def close(self) -> None:
        self._general.close()
        self._club.close()

    # ------------------------------------------------------------- helpers

    def _file_for(self, club_id: ClubId | None) -> sqlite3.Connection:
        if club_id is None:
            return self._general
        if club_id != self.club_id:
            raise CapabilityError(ErrorCode.NOT_AUTHORIZED, "cannot write another club's directory")
        return self._club

    def _put(self, table: str, key: str, club_id: ClubId | None, model: BaseModel) -> None:
        db = self._file_for(club_id)
        with db:
            db.execute(
                f"INSERT OR REPLACE INTO {table} (id, club_id, body) VALUES (?, ?, ?)",  # noqa: S608 (fixed table names)
                (key, club_id, model.model_dump_json()),
            )

    @staticmethod
    def _rows(db: sqlite3.Connection, table: str, model: type[M]) -> list[M]:
        rows = db.execute(f"SELECT body FROM {table} ORDER BY id").fetchall()  # noqa: S608 (fixed table names)
        return [model.model_validate_json(r[0]) for r in rows]

    # ------------------------------------------------------------ contacts

    def put_contact(self, contact: Contact) -> None:
        self._put("contacts", contact.contact_id, contact.club_id, contact)

    def contacts(self) -> list[Contact]:
        """AUB-wide contacts first, then the club's own."""
        return [*self._rows(self._general, "contacts", Contact), *self._rows(self._club, "contacts", Contact)]

    # -------------------------------------------------------------- assets

    def put_asset(self, asset: Asset) -> None:
        self._put("assets", asset.asset_id, asset.club_id, asset)

    def assets(self) -> list[Asset]:
        return [*self._rows(self._general, "assets", Asset), *self._rows(self._club, "assets", Asset)]

    # -------------------------------------------------------------- events

    def put_event(self, record: EventRecord) -> None:
        db = self._file_for(record.club_id)
        with db:
            db.execute(
                "INSERT OR REPLACE INTO events (id, club_id, on_date, body) VALUES (?, ?, ?, ?)",
                (record.event_id, record.club_id, record.on.isoformat(), record.model_dump_json()),
            )

    def events(self) -> list[EventRecord]:
        """The club's events, newest first."""
        rows = self._club.execute("SELECT body FROM events ORDER BY on_date DESC, id").fetchall()
        return [EventRecord.model_validate_json(r[0]) for r in rows]

    def event(self, event_id: EventId) -> EventRecord | None:
        row = self._club.execute("SELECT body FROM events WHERE id = ?", (event_id,)).fetchone()
        return EventRecord.model_validate_json(row[0]) if row else None
