"""Synthetic metadata fixtures; no provider or club documents."""

from datetime import timedelta
from decimal import Decimal

from clubops.contracts.agent import AgentRun, AgentStep, RunStatus, StepState
from clubops.contracts.common import Status, TraceMeta
from clubops.reports.otel_input import ModelObservation, RunObservation, StepWindow
from tests.factories import CLUB, NOW


def observation() -> RunObservation:
    run = AgentRun(
        run_id="run-synthetic",
        club_id=CLUB,
        event_id="ev-synthetic",
        status=RunStatus.DONE,
        steps=[AgentStep(n=1, tool="search-memory", text="Synthetic private description", state=StepState.DONE)],
        steps_used=1,
        step_limit=8,
        cost_usd=Decimal("0.003"),
        cost_limit_usd=Decimal("0.05"),
    )
    trace = TraceMeta(
        trace_id="trace-synthetic",
        capability="planner",
        capability_version="1.0.0",
        prompt_version="planner-v1",
        model="synthetic-model",
        started_at=NOW + timedelta(milliseconds=100),
        latency_ms=200,
        tokens_in=100,
        tokens_out=20,
        cost_usd=Decimal("0.003"),
        retries=1,
        replayed=True,
    )
    return RunObservation(
        run,
        NOW,
        NOW + timedelta(seconds=1),
        (StepWindow(1, NOW, NOW + timedelta(milliseconds=800)),),
        (ModelObservation(CLUB, run.run_id, 1, trace, Status.OK),),
    )
