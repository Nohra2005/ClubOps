"""Cross-cutting behaviour of every capability: authorization, retries, error mapping, tracing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import get_args

import pytest
from pydantic import BaseModel

from clubops.capabilities import registry
from clubops.capabilities.runner import CapabilityError, Outcome, Usage, run
from clubops.contracts.common import ErrorCode, Question, Role, Status
from clubops.contracts.event import EventSpec
from clubops.contracts.knowhow import Answer, AskRequest, GapReport, GapRequest
from clubops.contracts.planning import PlanRequest
from clubops.contracts.rules import RuleApplication, RuleApplicationRequest
from clubops.contracts.sponsors import NeedStatus, ReplacementRequest, SponsorNeed
from clubops.tracing import MemoryTracer
from tests.factories import CLUB, TODAY, actor

ASK = registry.get("ask")
REQUEST = AskRequest(club_id=CLUB, question="Who sponsored water last year?", as_of=date(2026, 10, 5))
NO_SLEEP = lambda _s: None  # noqa: E731


def unknown(_: object) -> Outcome[Answer]:
    return Outcome(data=Answer(known=False, text="Not in the club's know-how.", basis="none"))


def test_ok_result_and_one_trace_line() -> None:
    tracer = MemoryTracer()
    result = run(ASK, unknown, REQUEST, actor(), tracer)
    assert result.status is Status.OK
    assert len(tracer.records) == 1
    assert tracer.records[0][0].capability == "ask"


def test_retryable_error_is_retried_then_succeeds() -> None:
    calls = {"n": 0}

    def flaky(req: object) -> Outcome[Answer]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise CapabilityError(ErrorCode.RATE_LIMITED, "429")
        return unknown(req)

    result = run(ASK, flaky, REQUEST, actor(), MemoryTracer(), sleep=NO_SLEEP)
    assert result.status is Status.OK
    assert result.trace.retries == 1


def test_retries_stop_at_policy_limit() -> None:
    def always_timeout(_: object) -> Outcome[Answer]:
        raise CapabilityError(ErrorCode.UPSTREAM_TIMEOUT, "timeout")

    result = run(ASK, always_timeout, REQUEST, actor(), MemoryTracer(), sleep=NO_SLEEP)
    assert result.status is Status.FAILED
    assert result.error is not None and result.error.code is ErrorCode.UPSTREAM_TIMEOUT
    assert result.trace.retries == ASK.policy.max_retries


def test_injection_is_refused_without_retry() -> None:
    def injected(_: object) -> Outcome[Answer]:
        raise CapabilityError(ErrorCode.INJECTION_SUSPECTED, "source tried to give instructions")

    result = run(ASK, injected, REQUEST, actor(), MemoryTracer(), sleep=NO_SLEEP)
    assert result.error is not None and result.error.code is ErrorCode.INJECTION_SUSPECTED
    assert result.trace.retries == 0


def test_malformed_model_output_is_retried_then_reported() -> None:
    def malformed(_: object) -> Outcome[Answer]:
        Answer(known=True, text="yes", basis="verified")  # raises: no citations
        raise AssertionError("unreachable")

    result = run(ASK, malformed, REQUEST, actor(), MemoryTracer(), sleep=NO_SLEEP)
    assert result.error is not None and result.error.code is ErrorCode.MALFORMED_MODEL_OUTPUT
    assert result.trace.retries == ASK.policy.max_retries


def test_actor_from_another_club_is_refused() -> None:
    result = run(ASK, unknown, REQUEST, actor(club="other-club"), MemoryTracer())
    assert result.error is not None and result.error.code is ErrorCode.NOT_AUTHORIZED


def test_cabinet_only_capability_refuses_members() -> None:
    verify = registry.get("verify")
    result = run(verify, unknown, REQUEST, actor(Role.MEMBER), MemoryTracer())
    assert result.error is not None
    assert result.error.code in {ErrorCode.NOT_AUTHORIZED, ErrorCode.INVALID_INPUT}


def test_wrong_request_type_is_invalid_input() -> None:
    gaps = registry.get("find-gaps")
    result = run(gaps, unknown, REQUEST, actor(), MemoryTracer())
    assert result.error is not None and result.error.code is ErrorCode.INVALID_INPUT


def test_wrong_response_type_is_internal_error() -> None:
    gaps = registry.get("find-gaps")
    request = GapRequest(club_id=CLUB, as_of=date(2026, 10, 5))
    result = run(gaps, unknown, request, actor(), MemoryTracer())
    assert result.error is not None and result.error.code is ErrorCode.INTERNAL


def test_blocking_question_becomes_needs_input() -> None:
    gaps = registry.get("find-gaps")
    request = GapRequest(club_id=CLUB, as_of=date(2026, 10, 5))

    def ask_back(_: object) -> Outcome[GapReport]:
        return Outcome(questions=[Question(question_id="which-role", text="For which role?")])

    result = run(gaps, ask_back, request, actor(), MemoryTracer())
    assert result.status is Status.NEEDS_INPUT


# ------------------------------------------------------- club scoping, nested


def _nested_club_requests(club: str) -> list[tuple[str, BaseModel]]:
    spec = EventSpec(event_id="ev-spring-run", club_id=club, revision=1)
    rules = RuleApplication(event_id="ev-spring-run", spec_revision=1, rulebook=[], verdicts=[], requirements=[])
    need = SponsorNeed(
        need_id="water", event_id="ev-spring-run", category="water", description="Water", status=NeedStatus.OPEN
    )
    return [
        ("apply-rules", RuleApplicationRequest(spec=spec, as_of=TODAY)),
        ("plan-backward", PlanRequest(spec=spec, rules=rules, today=TODAY)),
        ("suggest-replacement", ReplacementRequest(club_id=club, need=need)),
    ]


@pytest.mark.parametrize(("name", "request_"), _nested_club_requests("other-club"))
def test_nested_club_id_from_another_club_is_refused(name: str, request_: BaseModel) -> None:
    called = {"n": 0}

    def must_not_run(_: object) -> Outcome[Answer]:
        called["n"] += 1
        raise AssertionError("capability ran for another club")

    result = run(registry.get(name), must_not_run, request_, actor(), MemoryTracer())
    assert result.error is not None and result.error.code is ErrorCode.NOT_AUTHORIZED
    assert called["n"] == 0


def _has_required_club_id(model: type[BaseModel]) -> bool:
    for name, info in model.model_fields.items():
        nullable = type(None) in get_args(info.annotation)
        if not info.is_required() or nullable:
            continue
        if name == "club_id":
            return True
        nested = info.annotation
        if isinstance(nested, type) and issubclass(nested, BaseModel) and _has_required_club_id(nested):
            return True
    return False


def test_every_request_names_its_club() -> None:
    # verify is exempt: AUB-wide rule proposals have no club, and the store checks the club itself
    # (tests/test_store.py::test_cannot_verify_another_clubs_know_how).
    unscoped = [s.name for s in registry.CAPABILITIES if s.name != "verify" and not _has_required_club_id(s.request)]
    assert unscoped == [], f"requests the runner cannot scope to a club: {unscoped}"


# ------------------------------------------------- fallback, timeout, usage


def not_known_fallback(_: object) -> Outcome[Answer]:
    return Outcome(data=Answer(known=False, text="Not known (fallback).", basis="none"))


def test_declared_fallback_runs_after_retries_and_is_marked_degraded() -> None:
    def always_timeout(_: object) -> Outcome[Answer]:
        raise CapabilityError(ErrorCode.UPSTREAM_TIMEOUT, "timeout")

    result = run(ASK, always_timeout, REQUEST, actor(), MemoryTracer(), fallback=not_known_fallback, sleep=NO_SLEEP)
    assert result.status is Status.OK
    assert result.degraded is True
    assert result.trace.retries == ASK.policy.max_retries


def test_budget_exceeded_goes_straight_to_fallback() -> None:
    def over_budget(_: object) -> Outcome[Answer]:
        raise CapabilityError(ErrorCode.BUDGET_EXCEEDED, "packet budget spent")

    result = run(ASK, over_budget, REQUEST, actor(), MemoryTracer(), fallback=not_known_fallback, sleep=NO_SLEEP)
    assert result.status is Status.OK and result.degraded is True
    assert result.trace.retries == 0


def test_refusals_never_fall_back() -> None:
    def injected(_: object) -> Outcome[Answer]:
        raise CapabilityError(ErrorCode.INJECTION_SUSPECTED, "source tried to give instructions")

    result = run(ASK, injected, REQUEST, actor(), MemoryTracer(), fallback=not_known_fallback, sleep=NO_SLEEP)
    assert result.status is Status.FAILED
    assert result.error is not None and result.error.code is ErrorCode.INJECTION_SUSPECTED


def test_attempt_slower_than_the_policy_timeout_is_discarded() -> None:
    now = {"t": 0.0}

    def clock() -> float:
        return now["t"]

    def slow(req: object) -> Outcome[Answer]:
        now["t"] += ASK.policy.timeout_s + 1
        return unknown(req)

    result = run(ASK, slow, REQUEST, actor(), MemoryTracer(), sleep=NO_SLEEP, clock=clock)
    assert result.status is Status.FAILED
    assert result.error is not None and result.error.code is ErrorCode.UPSTREAM_TIMEOUT
    assert result.trace.retries == ASK.policy.max_retries


def test_tokens_and_cost_of_failed_attempts_are_counted() -> None:
    spent = Usage(model="m", tokens_in=100, tokens_out=50, cost_usd=Decimal("0.01"))
    calls = {"n": 0}

    def malformed_then_ok(req: object) -> Outcome[Answer]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise CapabilityError(ErrorCode.MALFORMED_MODEL_OUTPUT, "bad json", usage=spent)
        return Outcome(data=unknown(req).data, usage=spent)

    result = run(ASK, malformed_then_ok, REQUEST, actor(), MemoryTracer(), sleep=NO_SLEEP)
    assert result.status is Status.OK
    assert (result.trace.tokens_in, result.trace.tokens_out) == (200, 100)
    assert result.trace.cost_usd == Decimal("0.02")
