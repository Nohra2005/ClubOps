"""The gate in front of every side effect. Returns None when execution is allowed."""

from __future__ import annotations

from datetime import datetime

from clubops.contracts.approvals import ApprovalDecision, Decision, ProposedAction, payload_sha256
from clubops.contracts.common import Error, ErrorCode


def authorize_execution(
    action: ProposedAction,
    decision: ApprovalDecision,
    now: datetime,
    executed_keys: set[str],
) -> Error | None:
    def deny(code: ErrorCode, message: str) -> Error:
        return Error(code=code, message=message)

    actor = decision.actor
    if decision.action_id != action.action_id:
        return deny(ErrorCode.INVALID_INPUT, "decision is for another action")
    if decision.decision is not Decision.APPROVE:
        return deny(ErrorCode.NOT_AUTHORIZED, "action was rejected")
    if not actor.verified:
        return deny(ErrorCode.NOT_AUTHORIZED, "approver is not authenticated with AUB")
    if actor.club_id != action.club_id:
        return deny(ErrorCode.NOT_AUTHORIZED, "approver belongs to another club")
    if not (actor.roles & action.approver_roles):
        return deny(ErrorCode.NOT_AUTHORIZED, "approver does not hold a role allowed to approve this action")
    current = payload_sha256(action.payload)
    if decision.payload_sha256 != current or action.payload_sha256 != current:
        return deny(ErrorCode.STALE_INPUT, "the payload changed after it was approved")
    if now > action.expires_at or decision.decided_at > action.expires_at:
        return deny(ErrorCode.STALE_INPUT, "the action expired")
    if action.idempotency_key in executed_keys:
        return deny(ErrorCode.CONFLICT, "already executed")
    return None
