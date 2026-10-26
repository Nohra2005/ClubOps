"""C-20: cumulative planning spend and metadata privacy with synthetic runs."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from clubops.contracts.agent import AgentRun, AgentStep, RunStatus, StepState
from clubops.reports.runs import RunRecord, read_runs, record_run, run_path, summarize_runs

NOW = datetime(2026, 10, 26, tzinfo=UTC)


def record(run_id: str, cost: str, status: RunStatus, steps: int = 1, at: datetime = NOW) -> RunRecord:
    return RunRecord(run_id=run_id, cost_usd=Decimal(cost), status=status, steps_used=steps, observed_at=at)


def test_cost_includes_failed_attempts_but_duplicate_snapshots_are_not_charged_twice() -> None:
    success = record("run-success", "0.03", RunStatus.DONE, 3)
    records = [
        record("run-success", "0.01", RunStatus.RUNNING),
        success,
        success,
        record("run-failed", "0.02", RunStatus.FAILED),
    ]
    assert summarize_runs(records, "2026-10") == {
        "recorded_runs": 2,
        "successful_plans": 1,
        "failed_runs": 1,
        "planner_steps": 4,
        "cost_usd": 0.05,
        "cost_per_successful_plan": 0.05,
    }
    assert summarize_runs([], "2026-10")["cost_per_successful_plan"] is None


def test_cross_month_continuation_counts_only_new_spend_in_beirut_time() -> None:
    october = record("run-continued", "0.03", RunStatus.AT_LIMIT, 8, datetime(2026, 10, 31, 20, tzinfo=UTC))
    november = record("run-continued", "0.05", RunStatus.DONE, 10, datetime(2026, 10, 31, 23, tzinfo=UTC))
    summary = summarize_runs([october, november, november], "2026-11")
    assert summary["cost_usd"] == 0.02 and summary["planner_steps"] == 2 and summary["successful_plans"] == 1


def test_run_recording_is_club_bound_and_never_writes_private_step_text(tmp_path: Path) -> None:
    run = AgentRun(
        run_id="run-example",
        club_id="running-club",
        status=RunStatus.RUNNING,
        steps=[AgentStep(n=1, tool="search-memory", text="PRIVATE PROMPT", state=StepState.RUNNING)],
        steps_used=1,
        step_limit=8,
        cost_usd=Decimal("0.001"),
        cost_limit_usd=Decimal("0.05"),
    )
    record_run(tmp_path, "running-club", run, NOW)
    path = run_path(tmp_path, "running-club")
    assert "PRIVATE PROMPT" not in path.read_text()
    assert len(read_runs(path)) == 1
    assert read_runs(run_path(tmp_path, "asme")) == []
    with pytest.raises(ValueError, match="run's club"):
        record_run(tmp_path, "asme", run, NOW)
    with pytest.raises(ValueError):
        run_path(tmp_path, "../another-club")


def test_broken_or_decreasing_metadata_never_produces_a_misleading_report(tmp_path: Path) -> None:
    path = tmp_path / "broken.jsonl"
    path.write_text('{"PRIVATE":"malformed"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid run metadata"):
        read_runs(path)
    with pytest.raises(ValueError, match="decreased"):
        summarize_runs(
            [record("run-example", "0.02", RunStatus.RUNNING), record("run-example", "0.01", RunStatus.DONE)], "2026-10"
        )
