"""Agent runs are saved so a run can wait for the user's answer across requests (or a restart).

Runs live in the club's own file (D-23), next to its know-how and events.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from clubops.agent.planner import RunState
from clubops.contracts.common import ClubId


class RunStore:
    def __init__(self, data_dir: Path, club_id: ClubId) -> None:
        path = data_dir / "clubs" / f"{club_id}.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.club_id = club_id
        self._db = sqlite3.connect(str(path))
        self._db.execute("CREATE TABLE IF NOT EXISTS agent_runs (run_id TEXT PRIMARY KEY, body TEXT NOT NULL)")

    def close(self) -> None:
        self._db.close()

    def save(self, state: RunState) -> None:
        if state.run.club_id != self.club_id:
            raise ValueError("a run is saved in its own club's file")
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO agent_runs (run_id, body) VALUES (?, ?)",
                (state.run.run_id, state.model_dump_json()),
            )

    def get(self, run_id: str) -> RunState | None:
        row = self._db.execute("SELECT body FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
        return RunState.model_validate_json(row[0]) if row else None
