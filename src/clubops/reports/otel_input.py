"""Explicit, in-memory producer boundary for C-25; not a new shared contract.

Only completed run snapshots are supported. Nothing is inferred from unrelated
JSONL records. Callers must obtain timing and associations at the actual call site.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from clubops.contracts.agent import AgentRun, RunStatus, StepState
from clubops.contracts.common import ErrorCode, Status, TraceMeta


@dataclass(frozen=True, repr=False)
class StepWindow:
    n: int
    started_at: datetime
    ended_at: datetime


@dataclass(frozen=True, repr=False)
class ModelObservation:
    club_id: str
    run_id: str
    step_n: int
    trace: TraceMeta
    status: Status
    error: ErrorCode | None = None


@dataclass(frozen=True, repr=False)
class RunObservation:
    run: AgentRun
    started_at: datetime
    ended_at: datetime
    steps: tuple[StepWindow, ...]
    calls: tuple[ModelObservation, ...]


def unix_nanos(value: datetime) -> int:
    """Exact integer conversion; reject naive, pre-epoch or out-of-range times."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Invalid telemetry observation.")
    delta = value.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    result = (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000
    if not 0 <= result < 2**64:
        raise ValueError("Invalid telemetry observation.")
    return result


def validate_observation(value: RunObservation) -> RunObservation:
    """Snapshot mutable nested models and fail with no raw values in diagnostics."""
    try:
        run = AgentRun.model_validate(value.run.model_dump())
        if run.status not in {RunStatus.DONE, RunStatus.FAILED, RunStatus.AT_LIMIT}:
            raise ValueError
        if len(run.steps) > 64 or len(value.calls) > 256:
            raise ValueError
        start, end = unix_nanos(value.started_at), unix_nanos(value.ended_at)
        if start > end or {s.n for s in value.steps} != {s.n for s in run.steps}:
            raise ValueError
        if len(value.steps) != len(run.steps) or any(s.state is StepState.RUNNING for s in run.steps):
            raise ValueError
        windows = {s.n: s for s in value.steps}
        for window in value.steps:
            if not start <= unix_nanos(window.started_at) <= unix_nanos(window.ended_at) <= end:
                raise ValueError
        calls: list[ModelObservation] = []
        seen: set[str] = set()
        for call in value.calls:
            trace = TraceMeta.model_validate(call.trace.model_dump())
            status = Status(call.status)
            error = ErrorCode(call.error) if call.error is not None else None
            if (call.club_id, call.run_id) != (run.club_id, run.run_id) or trace.trace_id in seen:
                raise ValueError
            seen.add(trace.trace_id)
            window = windows[call.step_n]
            call_end = trace.started_at + timedelta(milliseconds=trace.latency_ms)
            if not unix_nanos(window.started_at) <= unix_nanos(trace.started_at) <= unix_nanos(call_end):
                raise ValueError
            if unix_nanos(call_end) > unix_nanos(window.ended_at):
                raise ValueError
            if (status is Status.FAILED) != (error is not None):
                raise ValueError
            calls.append(ModelObservation(call.club_id, call.run_id, call.step_n, trace, status, error))
        return RunObservation(run, value.started_at, value.ended_at, tuple(value.steps), tuple(calls))
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
        raise ValueError("Invalid telemetry observation.") from None
