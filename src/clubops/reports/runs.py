"""Persist only approved run metadata, never step text, questions, prompts or answers."""

from __future__ import annotations

import threading
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, TypeAdapter, ValidationError

from clubops.contracts.agent import AgentRun, RunStatus
from clubops.contracts.common import ClubId, Contract, Slug

_LOCK = threading.Lock()
BEIRUT = ZoneInfo("Asia/Beirut")


class RunRecord(Contract):
    run_id: Slug
    observed_at: datetime
    status: RunStatus
    steps_used: int = Field(ge=0)
    cost_usd: Decimal = Field(ge=0)


def run_path(data_dir: Path, club_id: str) -> Path:
    club = TypeAdapter(ClubId).validate_python(club_id)
    return data_dir / "reports" / club / "runs.jsonl"


def record_run(data_dir: Path, club_id: str, run: AgentRun, observed_at: datetime) -> None:
    if run.club_id != club_id or observed_at.tzinfo is None:
        raise ValueError("Usage records require the run's club and an aware timestamp.")
    record = RunRecord(
        run_id=run.run_id, observed_at=observed_at, status=run.status, steps_used=run.steps_used, cost_usd=run.cost_usd
    )
    path = run_path(data_dir, club_id)
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write(record.model_dump_json() + "\n")


def read_runs(path: Path) -> list[RunRecord]:
    if not path.exists():
        return []
    records: list[RunRecord] = []
    with _LOCK, path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                record = RunRecord.model_validate_json(line)
                if record.observed_at.tzinfo is None:
                    raise ValueError("naive time")
            except (ValidationError, ValueError):
                raise ValueError(f"Invalid run metadata at line {number}; report not generated.") from None
            records.append(record)
    return records


def summarize_runs(records: Iterable[RunRecord], month: str) -> dict[str, int | float | None]:
    """Count cumulative snapshots once; cost in a later month includes only that month's increments."""
    datetime.strptime(month, "%Y-%m")
    latest: dict[str, RunRecord] = {}
    seen: set[str] = set()
    cost = Decimal(0)
    steps = successes = failures = 0
    for record in records:
        previous = latest.get(record.run_id)
        if previous and (record.cost_usd < previous.cost_usd or record.steps_used < previous.steps_used):
            raise ValueError("Run metadata decreased; report not generated.")
        if record.observed_at.astimezone(BEIRUT).strftime("%Y-%m") == month:
            seen.add(record.run_id)
            cost += record.cost_usd - (previous.cost_usd if previous else Decimal(0))
            steps += record.steps_used - (previous.steps_used if previous else 0)
            if record.status is RunStatus.DONE and (previous is None or previous.status is not RunStatus.DONE):
                successes += 1
            if record.status is RunStatus.FAILED and (previous is None or previous.status is not RunStatus.FAILED):
                failures += 1
        latest[record.run_id] = record
    return {
        "recorded_runs": len(seen),
        "successful_plans": successes,
        "failed_runs": failures,
        "planner_steps": steps,
        "cost_usd": float(cost),
        "cost_per_successful_plan": float(cost / successes) if successes else None,
    }
