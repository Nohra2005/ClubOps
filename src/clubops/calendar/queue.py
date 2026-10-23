"""Durable queue of approved calendar items awaiting Google sync."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from pathlib import Path

from clubops.calendar.sync import CalendarSync, SyncError, SyncResult
from clubops.contracts.calendar import CalendarItem
from clubops.contracts.common import Role


class SyncQueue:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS pending_calendar ("
                "club_id TEXT NOT NULL, item_id TEXT NOT NULL, item_json TEXT NOT NULL, "
                "last_error TEXT, PRIMARY KEY (club_id, item_id))"
            )

    def enqueue(self, item: CalendarItem, *, approved: bool) -> None:
        if not approved:
            raise ValueError("only approved calendar items may be queued")
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO pending_calendar (club_id, item_id, item_json, last_error) VALUES (?, ?, ?, NULL) "
                "ON CONFLICT (club_id, item_id) DO UPDATE SET item_json=excluded.item_json, last_error=NULL",
                (item.club_id, item.item_id, item.model_dump_json()),
            )

    def pending(self) -> list[CalendarItem]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT item_json FROM pending_calendar ORDER BY club_id, item_id").fetchall()
        return [CalendarItem.model_validate_json(row[0]) for row in rows]

    def drain(
        self, sync: CalendarSync, roles_for_club: Callable[[str], Mapping[Role, str]]
    ) -> list[tuple[CalendarItem, SyncResult]]:
        synced: list[tuple[CalendarItem, SyncResult]] = []
        for item in self.pending():
            try:
                result = sync.sync(item, approved=True, role_emails=roles_for_club(item.club_id))
            except SyncError as exc:
                with sqlite3.connect(self.path) as db:
                    db.execute(
                        "UPDATE pending_calendar SET last_error=? WHERE club_id=? AND item_id=?",
                        (str(exc), item.club_id, item.item_id),
                    )
                continue
            with sqlite3.connect(self.path) as db:
                db.execute(
                    "DELETE FROM pending_calendar WHERE club_id=? AND item_id=? AND item_json=?",
                    (item.club_id, item.item_id, item.model_dump_json()),
                )
            synced.append((item, result))
        return synced
