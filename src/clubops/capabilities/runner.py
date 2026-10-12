"""Runs any capability under its declared policy and turns the outcome into a ``Result``.

This is where the cross-cutting rules live, so individual capabilities stay simple:
authorization, club scoping, input/output type checks, retries for retryable errors,
and one trace record per call. Traces never contain request or response bodies.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from clubops.capabilities.registry import CapabilitySpec
from clubops.contracts.common import (
    ERROR_BEHAVIOR,
    Actor,
    Error,
    ErrorCode,
    Issue,
    Question,
    Recovery,
    Result,
    Status,
    TraceMeta,
)

T = TypeVar("T", bound=BaseModel)


class CapabilityError(Exception):
    """Raised inside a capability for an expected failure; converted to a FAILED result."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Usage:
    model: str | None = None
    prompt_version: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0")
    replayed: bool = False


@dataclass(frozen=True)
class Outcome(Generic[T]):
    data: T | None = None
    issues: list[Issue] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    degraded: bool = False
    usage: Usage = field(default_factory=Usage)


class Tracer(Protocol):
    def record(self, trace: TraceMeta, status: Status, error: ErrorCode | None) -> None: ...


def run(
    spec: CapabilitySpec,
    fn: Callable[[BaseModel], Outcome[T]],
    request: BaseModel,
    actor: Actor,
    tracer: Tracer,
    *,
    trace_id: str | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Result[T]:
    trace_id = trace_id or uuid.uuid4().hex
    started = datetime.now(UTC)
    t0 = time.perf_counter()
    retries = 0
    usage = Usage()

    def finish(
        status: Status,
        *,
        data: T | None = None,
        error: Error | None = None,
        issues: list[Issue] | None = None,
        questions: list[Question] | None = None,
        degraded: bool = False,
    ) -> Result[T]:
        trace = TraceMeta(
            trace_id=trace_id,
            capability=spec.name,
            capability_version=spec.version,
            prompt_version=usage.prompt_version,
            model=usage.model,
            started_at=started,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            tokens_in=usage.tokens_in,
            tokens_out=usage.tokens_out,
            cost_usd=usage.cost_usd,
            retries=retries,
            replayed=usage.replayed,
        )
        tracer.record(trace, status, error.code if error else None)
        return Result[T](
            status=status,
            data=data,
            error=error,
            issues=issues or [],
            questions=questions or [],
            degraded=degraded,
            trace=trace,
        )

    def fail(code: ErrorCode, message: str) -> Result[T]:
        return finish(Status.FAILED, error=Error(code=code, message=message))

    if not isinstance(request, spec.request):
        return fail(ErrorCode.INVALID_INPUT, f"expected {spec.request.__name__}, got {type(request).__name__}")
    if spec.requires_cabinet and not actor.is_cabinet:
        return fail(ErrorCode.NOT_AUTHORIZED, "only verified cabinet members can do this")
    request_club = getattr(request, "club_id", None)
    if request_club is not None and request_club != actor.club_id:
        return fail(ErrorCode.NOT_AUTHORIZED, "actor belongs to another club")

    while True:
        try:
            outcome = fn(request)
        except CapabilityError as exc:
            code, message = exc.code, exc.message
        except ValidationError as exc:
            code, message = ErrorCode.MALFORMED_MODEL_OUTPUT, f"output failed validation: {exc.error_count()} errors"
        else:
            usage = outcome.usage
            break
        if ERROR_BEHAVIOR[code] is Recovery.RETRY and retries < spec.policy.max_retries:
            retries += 1
            sleep(min(2.0**retries, 10.0))
            continue
        return fail(code, message)

    if outcome.data is None:
        if any(q.blocking for q in outcome.questions):
            return finish(Status.NEEDS_INPUT, issues=outcome.issues, questions=outcome.questions)
        return fail(ErrorCode.INTERNAL, "capability returned neither data nor a blocking question")
    if not isinstance(outcome.data, spec.response):
        return fail(ErrorCode.INTERNAL, f"expected {spec.response.__name__}, got {type(outcome.data).__name__}")
    return finish(
        Status.OK,
        data=outcome.data,
        issues=outcome.issues,
        questions=outcome.questions,
        degraded=outcome.degraded,
    )
