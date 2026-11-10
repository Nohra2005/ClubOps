"""Explicit synthetic trace fixture for the local viewer; never calls a model.

python -m clubops.reports.otel_demo --endpoint http://127.0.0.1:4318/v1/traces
No endpoint/environment -> disabled, no network. Times/counts are fixture data,
not measured agent performance. Kept outside the live application's entry point.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from clubops.contracts.agent import AgentRun, AgentStep, RunStatus, StepState
from clubops.contracts.common import Status, TraceMeta
from clubops.reports.otel import export_run
from clubops.reports.otel_input import ModelObservation, RunObservation, StepWindow
from clubops.reports.otel_payload import PublicLabels

DEMO_LABELS = PublicLabels(
    tools=frozenset({"search-memory", "apply-rules"}),
    capabilities=frozenset({"synthetic-planner"}),
    capability_versions=frozenset({"1.0.0"}),
    prompt_versions=frozenset({"synthetic-v1"}),
    models=frozenset({"synthetic-no-provider"}),
)


def synthetic_run() -> RunObservation:
    start = datetime.now(UTC) - timedelta(seconds=3)
    run = AgentRun(
        run_id="run-synthetic-otel",
        club_id="synthetic-club",
        event_id="ev-synthetic-otel",
        status=RunStatus.DONE,
        steps=[
            AgentStep(n=n, tool=tool, text="Synthetic fixture, not a real event", state=StepState.DONE)
            for n, tool in enumerate(("search-memory", "apply-rules"), 1)
        ],
        steps_used=2,
        step_limit=8,
        cost_usd=Decimal(0),
        cost_limit_usd=Decimal("0.05"),
    )
    steps = tuple(StepWindow(n, start + timedelta(seconds=n - 1), start + timedelta(seconds=n)) for n in (1, 2))
    calls = tuple(
        ModelObservation(
            run.club_id,
            run.run_id,
            window.n,
            TraceMeta(
                trace_id=f"synthetic-call-{window.n}",
                capability="synthetic-planner",
                capability_version="1.0.0",
                prompt_version="synthetic-v1",
                model="synthetic-no-provider",
                started_at=window.started_at + timedelta(milliseconds=100),
                latency_ms=200,
                tokens_in=0,
                tokens_out=0,
                cost_usd=Decimal(0),
                replayed=True,
            ),
            Status.OK,
        )
        for window in steps
    )
    return RunObservation(run, start, start + timedelta(seconds=2), steps, calls)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a synthetic completed-run fixture; no AI/provider calls.")
    parser.add_argument("--endpoint", help="Full trusted OTLP/HTTP JSON traces URL; otherwise trace-specific env var.")
    args = parser.parse_args(argv)
    result = export_run(synthetic_run(), endpoint=args.endpoint, labels=DEMO_LABELS)
    print(json.dumps(asdict(result)))
    return 0 if result.outcome in {"accepted", "disabled"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
