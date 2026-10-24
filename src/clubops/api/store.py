"""What the API keeps for each club, next to its know-how in the club's own file (D-23).

- planned events: the event details, the plan, the rule check, and who approved it;
- task changes made on the event page (done, new owner);
- calendar items sent after approval (Joey's sync reads these);
- what each agent run cost, for the Usage screen.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from clubops.contracts.calendar import CalendarItem
from clubops.contracts.event import EventSpec
from clubops.contracts.planning import Plan
from clubops.contracts.rules import RuleApplication

_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_events (
    event_id TEXT PRIMARY KEY, spec TEXT NOT NULL, plan TEXT, rules TEXT, run_id TEXT,
    approved_by TEXT, approved_at TEXT, approved_revision INTEGER);
CREATE TABLE IF NOT EXISTS api_tasks (task_id TEXT PRIMARY KEY, state TEXT, owner_role TEXT);
CREATE TABLE IF NOT EXISTS api_calendar (item_id TEXT PRIMARY KEY, event_id TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS api_usage (run_id TEXT PRIMARY KEY, month TEXT NOT NULL, steps INTEGER NOT NULL,
    cost TEXT NOT NULL);
"""


@dataclass
class PlannedEvent:
    spec: EventSpec
    plan: Plan | None
    rules: RuleApplication | None
    run_id: str | None
    approved_by: str | None = None
    approved_at: str | None = None
    approved_revision: int | None = None

    @property
    def plan_outdated(self) -> bool:
        return self.plan is None or self.plan.spec_revision != self.spec.revision


class ApiStore:
    def __init__(self, data_dir: Path, club_id: str) -> None:
        path = data_dir / "clubs" / f"{club_id}.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.executescript(_SCHEMA)

    def close(self) -> None:
        self._db.close()

    # ---------------------------------------------------------------- events

    def save_event(self, event: PlannedEvent) -> None:
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO api_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event.spec.event_id,
                    event.spec.model_dump_json(),
                    event.plan.model_dump_json() if event.plan else None,
                    event.rules.model_dump_json() if event.rules else None,
                    event.run_id,
                    event.approved_by,
                    event.approved_at,
                    event.approved_revision,
                ),
            )

    def event(self, event_id: str) -> PlannedEvent | None:
        row = self._db.execute("SELECT * FROM api_events WHERE event_id = ?", (event_id,)).fetchone()
        if row is None:
            return None
        return PlannedEvent(
            spec=EventSpec.model_validate_json(row[1]),
            plan=Plan.model_validate_json(row[2]) if row[2] else None,
            rules=RuleApplication.model_validate_json(row[3]) if row[3] else None,
            run_id=row[4],
            approved_by=row[5],
            approved_at=row[6],
            approved_revision=row[7],
        )

    def events(self) -> list[PlannedEvent]:
        ids = [r[0] for r in self._db.execute("SELECT event_id FROM api_events").fetchall()]
        return [e for e in (self.event(i) for i in ids) if e is not None]

    # ----------------------------------------------------------------- tasks

    def task_changes(self) -> dict[str, tuple[str | None, str | None]]:
        rows = self._db.execute("SELECT task_id, state, owner_role FROM api_tasks").fetchall()
        return {r[0]: (r[1], r[2]) for r in rows}

    def change_task(self, task_id: str, state: str | None, owner_role: str | None) -> None:
        old_state, old_owner = self.task_changes().get(task_id, (None, None))
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO api_tasks VALUES (?, ?, ?)",
                (task_id, state or old_state, owner_role or old_owner),
            )

    # -------------------------------------------------------------- calendar

    def put_calendar(self, items: list[CalendarItem]) -> None:
        with self._db:
            for item in items:
                self._db.execute(
                    "INSERT OR REPLACE INTO api_calendar VALUES (?, ?, ?)",
                    (item.item_id, item.event_id, item.model_dump_json()),
                )

    def calendar(self) -> list[CalendarItem]:
        rows = self._db.execute("SELECT body FROM api_calendar ORDER BY item_id").fetchall()
        return [CalendarItem.model_validate_json(r[0]) for r in rows]

    # ----------------------------------------------------------------- usage

    def record_usage(self, run_id: str, when: datetime, steps: int, cost: Decimal) -> None:
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO api_usage VALUES (?, ?, ?, ?)",
                (run_id, when.strftime("%Y-%m"), steps, str(cost)),
            )

    def usage(self, month: str) -> tuple[int, Decimal]:
        rows = self._db.execute("SELECT steps, cost FROM api_usage WHERE month = ?", (month,)).fetchall()
        return sum(r[0] for r in rows), sum((Decimal(r[1]) for r in rows), Decimal("0"))
