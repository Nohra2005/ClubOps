"""Cross-cutting behaviour of every capability: authorization, retries, error mapping, tracing."""

from __future__ import annotations

from datetime import date

from clubops.capabilities import registry
from clubops.capabilities.runner import CapabilityError, Outcome, run
from clubops.contracts.common import ErrorCode, Question, Role, Status
from clubops.contracts.knowhow import Answer, AskRequest, GapReport, GapRequest
from clubops.tracing import MemoryTracer
from tests.factories import CLUB, actor

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
