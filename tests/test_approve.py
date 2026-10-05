"""The approval gate: no side effect without a matching approval from an authorized member."""

from __future__ import annotations

from datetime import timedelta

from clubops.capabilities.approve import authorize_execution
from clubops.contracts.approvals import (
    ApprovalDecision,
    Decision,
    EmailPayload,
    ProposedAction,
    Risk,
    payload_sha256,
)
from clubops.contracts.common import ErrorCode, Role
from tests.factories import CLUB, NOW, actor

PAYLOAD = EmailPayload(to=["sponsor@example.com"], subject="Water for the fall run", body="Hello")
ACTION = ProposedAction(
    action_id="a-1",
    club_id=CLUB,
    payload=PAYLOAD,
    payload_sha256=payload_sha256(PAYLOAD),
    preview="Email",
    risk=Risk.MEDIUM,
    proposed_by="suggest-replacement",
    approver_roles=frozenset({Role.SPONSORSHIP, Role.PRESIDENT}),
    idempotency_key="k-1",
    created_at=NOW,
    expires_at=NOW + timedelta(days=2),
)


def decide(**kw) -> ApprovalDecision:  # type: ignore[no-untyped-def]
    base = {
        "action_id": "a-1",
        "payload_sha256": ACTION.payload_sha256,
        "decision": Decision.APPROVE,
        "actor": actor(Role.SPONSORSHIP),
        "decided_at": NOW,
    }
    return ApprovalDecision(**{**base, **kw})


def code(
    decision: ApprovalDecision, action: ProposedAction = ACTION, executed: set[str] | None = None
) -> ErrorCode | None:
    err = authorize_execution(action, decision, NOW + timedelta(hours=1), executed or set())
    return err.code if err else None


def test_authorized_approval_passes() -> None:
    assert code(decide()) is None


def test_rejection_blocks() -> None:
    assert code(decide(decision=Decision.REJECT)) is ErrorCode.NOT_AUTHORIZED


def test_payload_edited_after_approval_is_blocked() -> None:
    edited = EmailPayload(to=["attacker@example.com"], subject=PAYLOAD.subject, body=PAYLOAD.body)
    tampered = ProposedAction.model_validate(
        {**ACTION.model_dump(), "payload": edited.model_dump(), "payload_sha256": payload_sha256(edited)}
    )
    assert code(decide(), action=tampered) is ErrorCode.STALE_INPUT


def test_role_without_permission_is_blocked() -> None:
    assert code(decide(actor=actor(Role.COMMUNICATIONS))) is ErrorCode.NOT_AUTHORIZED


def test_unauthenticated_approver_is_blocked() -> None:
    assert code(decide(actor=actor(Role.SPONSORSHIP, verified=False))) is ErrorCode.NOT_AUTHORIZED


def test_approver_from_another_club_is_blocked() -> None:
    assert code(decide(actor=actor(Role.SPONSORSHIP, club="other-club"))) is ErrorCode.NOT_AUTHORIZED


def test_expired_action_is_blocked() -> None:
    err = authorize_execution(ACTION, decide(), NOW + timedelta(days=3), set())
    assert err is not None and err.code is ErrorCode.STALE_INPUT


def test_second_execution_is_blocked() -> None:
    assert code(decide(), executed={"k-1"}) is ErrorCode.CONFLICT


def test_decision_for_another_action_is_rejected() -> None:
    assert code(decide(action_id="a-2")) is ErrorCode.INVALID_INPUT
