"""Durable calendar state and pending Google writes, including trusted-mail deadlines."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from contextlib import closing
from pathlib import Path

from clubops.calendar.items import deadline_items
from clubops.calendar.sync import CalendarSync, SyncError, SyncResult
from clubops.contracts.calendar import (
    CalendarItem,
    DeadlineItems,
    DeadlineTasksRequest,
    HeldDeadline,
    ItemOrigin,
    ItemStatus,
)
from clubops.contracts.common import Role


class SyncQueue:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS pending_calendar ("
                "club_id TEXT NOT NULL, item_id TEXT NOT NULL, item_json TEXT NOT NULL, "
                "last_error TEXT, PRIMARY KEY (club_id, item_id))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS calendar_state ("
                "club_id TEXT NOT NULL, item_id TEXT NOT NULL, item_json TEXT NOT NULL, "
                "PRIMARY KEY (club_id, item_id))"
            )
            db.execute("INSERT OR IGNORE INTO calendar_state SELECT club_id, item_id, item_json FROM pending_calendar")
            db.execute(
                "CREATE TABLE IF NOT EXISTS held_calendar ("
                "club_id TEXT NOT NULL, source_key TEXT NOT NULL, held_json TEXT NOT NULL, "
                "PRIMARY KEY (club_id, source_key))"
            )

    @staticmethod
    def _save(db: sqlite3.Connection, item: CalendarItem) -> None:
        values = (item.club_id, item.item_id, item.model_dump_json())
        db.execute(
            "INSERT INTO calendar_state VALUES (?, ?, ?) "
            "ON CONFLICT (club_id, item_id) DO UPDATE SET item_json=excluded.item_json",
            values,
        )
        db.execute(
            "INSERT INTO pending_calendar (club_id, item_id, item_json, last_error) VALUES (?, ?, ?, NULL) "
            "ON CONFLICT (club_id, item_id) DO UPDATE SET item_json=excluded.item_json, last_error=NULL",
            values,
        )

    def enqueue(self, item: CalendarItem, *, approved: bool) -> None:
        if not approved:
            raise ValueError("only approved calendar items may be queued")
        with closing(sqlite3.connect(self.path)) as db, db:
            self._save(db, item)

    def enqueue_deadlines(self, request: DeadlineTasksRequest, *, source_key: str) -> DeadlineItems:
        """Backend supplies verified trust and a stable mail key; save tasks and holds atomically.

        Never call this from untrusted mail or a browser-supplied trust flag. Persisted state, rather than a
        caller's potentially stale ``existing`` snapshot, protects edits across sync and process restarts.
        """
        if not source_key.strip() or len(source_key) > 200:
            raise ValueError("a bounded stable mail key is required")
        if not request.trusted:
            raise ValueError("only mail that passed every check adds calendar tasks")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing = self._items(db, request.club_id)
            result = deadline_items(request.model_copy(update={"existing": existing}))
            for item in result.items:
                self._save(db, item)
            db.execute(
                "INSERT INTO held_calendar VALUES (?, ?, ?) "
                "ON CONFLICT (club_id, source_key) DO UPDATE SET held_json=excluded.held_json",
                (request.club_id, source_key, result.model_dump_json()),
            )
        return result

    @staticmethod
    def _items(db: sqlite3.Connection, club_id: str) -> list[CalendarItem]:
        rows = db.execute(
            "SELECT item_json FROM calendar_state WHERE club_id=? ORDER BY item_id", (club_id,)
        ).fetchall()
        return [CalendarItem.model_validate_json(row[0]) for row in rows]

    def items(self, club_id: str) -> list[CalendarItem]:
        """Authoritative local state, including cancelled tombstones; backend must authorize the club."""
        with closing(sqlite3.connect(self.path)) as db:
            return self._items(db, club_id)

    def held(self, club_id: str) -> dict[str, list[HeldDeadline]]:
        """Holds by mail key for an authorized Calendar/Review view; never sent to Google."""
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute(
                "SELECT source_key, held_json FROM held_calendar WHERE club_id=? ORDER BY source_key", (club_id,)
            ).fetchall()
        return {key: result.held for key, raw in rows if (result := DeadlineItems.model_validate_json(raw)).held}

    def change(self, item: CalendarItem, *, approved: bool) -> None:
        """An authorized person's edit/removal; preserve the id and block later automatic overwrites."""
        if not approved:
            raise ValueError("a person's calendar change requires approval")
        changed = CalendarItem.model_validate(
            {**item.model_dump(), "origin": ItemOrigin.PERSON, "edited_by_person": True}
        )
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if not any(old.item_id == item.item_id for old in self._items(db, item.club_id)):
                raise ValueError("no calendar item with this id in this club")
            self._save(db, changed)

    def remove(self, club_id: str, item_id: str, *, approved: bool) -> None:
        """Keep a protected cancellation tombstone so a mail replay cannot resurrect the task."""
        if not approved:
            raise ValueError("a person's calendar change requires approval")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            item = next((old for old in self._items(db, club_id) if old.item_id == item_id), None)
            if item is None:
                raise ValueError("no calendar item with this id in this club")
            self._save(
                db,
                item.model_copy(
                    update={"status": ItemStatus.CANCELLED, "origin": ItemOrigin.PERSON, "edited_by_person": True}
                ),
            )

    def pending(self, club_id: str | None = None) -> list[CalendarItem]:
        with closing(sqlite3.connect(self.path)) as db, db:
            rows = db.execute(
                "SELECT item_json FROM pending_calendar WHERE (? IS NULL OR club_id = ?) ORDER BY club_id, item_id",
                (club_id, club_id),
            ).fetchall()
        return [CalendarItem.model_validate_json(row[0]) for row in rows]

    def drain(
        self, sync: CalendarSync, roles_for_club: Callable[[str], Mapping[Role, str]], club_id: str | None = None
    ) -> list[tuple[CalendarItem, SyncResult]]:
        """Send what waits, for one club when ``club_id`` is given (each club has its own Google key, T-46)."""
        synced: list[tuple[CalendarItem, SyncResult]] = []
        for item in self.pending(club_id):
            try:
                result = sync.sync(
                    item,
                    approved=item.origin is not ItemOrigin.MAIL,
                    trusted_mail=item.origin is ItemOrigin.MAIL,
                    role_emails=roles_for_club(item.club_id),
                )
            except SyncError as exc:
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        "UPDATE pending_calendar SET last_error=? WHERE club_id=? AND item_id=?",
                        (str(exc), item.club_id, item.item_id),
                    )
                continue
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute(
                    "DELETE FROM pending_calendar WHERE club_id=? AND item_id=? AND item_json=?",
                    (item.club_id, item.item_id, item.model_dump_json()),
                )
            synced.append((item, result))
        return synced
