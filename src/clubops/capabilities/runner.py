"""Runs any capability under its declared policy and turns the outcome into a ``Result``.

This is where the cross-cutting rules live, so individual capabilities stay simple:
authorization, club scoping, input/output type checks, retries for retryable errors,
the per-attempt timeout, the declared fallback, and one trace record per call.
Traces never contain request or response bodies.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterator
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


@dataclass(frozen=True)
class Usage:
    model: str | None = None
    prompt_version: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0")
    replayed: bool = False

    def __add__(self, other: Usage) -> Usage:
        """Combine two attempts: tokens and cost add up; the latest model and prompt version win."""
        return Usage(
            model=other.model or self.model,
            prompt_version=other.prompt_version or self.prompt_version,
            tokens_in=self.tokens_in + other.tokens_in,
            tokens_out=self.tokens_out + other.tokens_out,
            cost_usd=self.cost_usd + other.cost_usd,
            replayed=self.replayed or other.replayed,
        )


class CapabilityError(Exception):
    """Raised inside a capability for an expected failure; converted to a FAILED result.

    ``usage`` carries what the failed attempt spent, so retries and failures still count
    toward cost (a model call that returned malformed output was still paid for).
    """

    def __init__(self, code: ErrorCode, message: str, usage: Usage | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.usage = usage or Usage()


@dataclass(frozen=True)
class Outcome(Generic[T]):
    data: T | None = None
    issues: list[Issue] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    degraded: bool = False
    usage: Usage = field(default_factory=Usage)


class Tracer(Protocol):
    def record(self, trace: TraceMeta, status: Status, error: ErrorCode | None) -> None: ...


def club_ids(value: object) -> Iterator[str]:
    """Every ``club_id`` anywhere in a request, however deeply nested (e.g. ``spec.club_id``)."""
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            child = getattr(value, name)
            if name == "club_id" and isinstance(child, str):
                yield child
            else:
                yield from club_ids(child)
    elif isinstance(value, list | tuple | set | frozenset):
        for child in value:
            yield from club_ids(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from club_ids(child)


def run(
    spec: CapabilitySpec,
    fn: Callable[[BaseModel], Outcome[T]],
    request: BaseModel,
    actor: Actor,
    tracer: Tracer,
    *,
    trace_id: str | None = None,
    fallback: Callable[[BaseModel], Outcome[T]] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.perf_counter,
) -> Result[T]:
    """Run ``fn`` under ``spec``'s policy.

    ``fallback`` is the code behind the spec's declared fallback. It runs when retries are
    exhausted or the budget is exceeded, and its data is returned with ``degraded=True``.
    It never runs for refusals (unauthorized, injection), which must stay refusals.

    An attempt that takes longer than ``policy.timeout_s`` is treated as an upstream timeout
    and its late answer is discarded. The model client also sets its own request timeout from
    the policy, so in practice slow calls are cut off before this check.
    """
    trace_id = trace_id or uuid.uuid4().hex
    started = datetime.now(UTC)
    t0 = clock()
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
            latency_ms=int((clock() - t0) * 1000),
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
    if any(club != actor.club_id for club in club_ids(request)):
        return fail(ErrorCode.NOT_AUTHORIZED, "actor belongs to another club")

    while True:
        attempt_started = clock()
        try:
            outcome = fn(request)
        except CapabilityError as exc:
            code, message = exc.code, exc.message
            usage = usage + exc.usage
        except ValidationError as exc:
            code, message = ErrorCode.MALFORMED_MODEL_OUTPUT, f"output failed validation: {exc.error_count()} errors"
        else:
            usage = usage + outcome.usage
            if clock() - attempt_started <= spec.policy.timeout_s:
                break
            code, message = ErrorCode.UPSTREAM_TIMEOUT, f"attempt exceeded {spec.policy.timeout_s}s; answer discarded"
        recovery = ERROR_BEHAVIOR[code]
        if recovery is Recovery.RETRY and retries < spec.policy.max_retries:
            retries += 1
            sleep(min(2.0**retries, 10.0))
            continue
        if fallback is not None and recovery in (Recovery.RETRY, Recovery.FALLBACK):
            try:
                outcome = fallback(request)
            except CapabilityError as exc:
                usage = usage + exc.usage
                return fail(exc.code, f"{message}; fallback also failed: {exc.message}")
            usage = usage + outcome.usage
            if outcome.data is None or not isinstance(outcome.data, spec.response):
                return fail(code, f"{message}; fallback produced no usable data")
            return finish(
                Status.OK,
                data=outcome.data,
                issues=outcome.issues,
                questions=outcome.questions,
                degraded=True,
            )
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
