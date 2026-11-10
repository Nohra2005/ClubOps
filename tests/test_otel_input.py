from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest

from clubops.contracts.agent import RunStatus, StepState
from clubops.contracts.common import ErrorCode, Status
from clubops.reports.otel_input import StepWindow, unix_nanos, validate_observation
from tests.otel_fixtures import observation


def test_snapshot_and_exact_timestamps() -> None:
    value = observation()
    snapshot = validate_observation(value)
    value.run.steps.clear()
    assert len(snapshot.run.steps) == 1
    instant = datetime(2026, 1, 1, 0, 0, 0, 123456, tzinfo=UTC)
    assert unix_nanos(instant) == 1767225600123456000
    assert unix_nanos(instant.astimezone(timezone(timedelta(hours=2)))) == unix_nanos(instant)


@pytest.mark.parametrize(
    "case",
    [
        "club",
        "run",
        "step",
        "duplicate",
        "naive",
        "outside",
        "reverse",
        "missing",
        "duplicate-step",
        "running",
        "step-running",
        "count",
        "too-many",
        "bad-contract",
        "error",
    ],
)
def test_invalid_observations_have_sanitized_errors(case: str) -> None:
    value = observation()
    call = value.calls[0]
    if case == "club":
        value = replace(value, calls=(replace(call, club_id="private-canary"),))
    elif case == "run":
        value = replace(value, calls=(replace(call, run_id="private-canary"),))
    elif case == "step":
        value = replace(value, calls=(replace(call, step_n=99),))
    elif case == "duplicate":
        value = replace(value, calls=(call, call))
    elif case == "naive":
        value = replace(value, started_at=value.started_at.replace(tzinfo=None))
    elif case == "outside":
        value = replace(value, steps=(StepWindow(1, value.started_at, call.trace.started_at),))
    elif case == "reverse":
        value = replace(value, ended_at=value.started_at - timedelta(seconds=1))
    elif case == "missing":
        value = replace(value, steps=())
    elif case == "duplicate-step":
        value = replace(value, steps=value.steps * 2)
    elif case == "running":
        value = replace(value, run=value.run.model_copy(update={"status": RunStatus.RUNNING}))
    elif case == "step-running":
        step = value.run.steps[0].model_copy(update={"state": StepState.RUNNING})
        value = replace(value, run=value.run.model_copy(update={"steps": [step]}))
    elif case == "count":
        value = replace(value, run=value.run.model_copy(update={"steps_used": 0}))
    elif case == "too-many":
        value = replace(value, calls=value.calls * 257)
    elif case == "bad-contract":
        value = replace(value, calls=(replace(call, trace=call.trace.model_copy(update={"tokens_in": -1})),))
    elif case == "error":
        value = replace(value, calls=(replace(call, error=ErrorCode.INTERNAL),))
    with pytest.raises(ValueError, match=r"^Invalid telemetry observation\.$"):
        validate_observation(value)


def test_failed_call_requires_typed_error() -> None:
    value = observation()
    call = replace(value.calls[0], status=Status.FAILED, error=ErrorCode.UPSTREAM_TIMEOUT)
    assert validate_observation(replace(value, calls=(call,))).calls[0].error is ErrorCode.UPSTREAM_TIMEOUT
    with pytest.raises(ValueError, match="Invalid telemetry observation"):
        validate_observation(replace(value, calls=(replace(call, error=None),)))


@pytest.mark.parametrize(
    "instant", [datetime(2026, 1, 1), datetime(1969, 1, 1, tzinfo=UTC), datetime.max.replace(tzinfo=UTC)]
)
def test_invalid_epoch_times(instant: datetime) -> None:
    with pytest.raises(ValueError, match="Invalid telemetry observation"):
        unix_nanos(instant)
