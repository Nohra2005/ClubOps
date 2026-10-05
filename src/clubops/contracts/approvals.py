"""Every side effect goes through here. Agents propose; verified cabinet members decide.

An approval is bound to the SHA-256 of the exact payload. Editing the payload after
approval voids the approval. ``idempotency_key`` stops a retry from executing twice.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import EmailStr, Field, model_validator

from clubops.contracts.common import Actor, ClubId, Contract, EventId, MemberId, Role, Slug


class ActionKind(StrEnum):
    SEND_EMAIL = "send_email"
    SEND_CALENDAR_INVITE = "send_calendar_invite"
    SUBMIT_PROPOSAL = "submit_proposal"
    SHARE_REMINDER = "share_reminder"
    SIGN_OFF_HANDOVER = "sign_off_handover"
    TRANSFER_ROLE = "transfer_role"


class EmailPayload(Contract):
    kind: Literal[ActionKind.SEND_EMAIL] = ActionKind.SEND_EMAIL
    to: list[EmailStr] = Field(min_length=1, max_length=10)
    subject: str = Field(max_length=200)
    body: str = Field(max_length=10_000)
    attachments: list[str] = Field(default_factory=list)


class CalendarInvitePayload(Contract):
    kind: Literal[ActionKind.SEND_CALENDAR_INVITE] = ActionKind.SEND_CALENDAR_INVITE
    to: list[EmailStr] = Field(min_length=1)
    title: str = Field(max_length=200)
    start: datetime
    end: datetime
    location: str = Field(max_length=200)


class SubmitProposalPayload(Contract):
    """The agent prepares; a human submits on the OSA form. Executing marks it as submitted."""

    kind: Literal[ActionKind.SUBMIT_PROPOSAL] = ActionKind.SUBMIT_PROPOSAL
    event_id: EventId
    spec_revision: int = Field(ge=1)
    draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ShareReminderPayload(Contract):
    """A WhatsApp text handed to the communications officer to copy and send."""

    kind: Literal[ActionKind.SHARE_REMINDER] = ActionKind.SHARE_REMINDER
    event_id: EventId
    recipient: MemberId
    text: str = Field(max_length=1500)
    send_at: datetime


class SignOffHandoverPayload(Contract):
    kind: Literal[ActionKind.SIGN_OFF_HANDOVER] = ActionKind.SIGN_OFF_HANDOVER
    pack_id: Slug
    pack_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class TransferRolePayload(Contract):
    kind: Literal[ActionKind.TRANSFER_ROLE] = ActionKind.TRANSFER_ROLE
    role: Role
    outgoing: MemberId
    incoming: MemberId


Payload = Annotated[
    EmailPayload
    | CalendarInvitePayload
    | SubmitProposalPayload
    | ShareReminderPayload
    | SignOffHandoverPayload
    | TransferRolePayload,
    Field(discriminator="kind"),
]


def payload_sha256(payload: Payload) -> str:
    return hashlib.sha256(payload.model_dump_json().encode()).hexdigest()


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProposedAction(Contract):
    action_id: Slug
    club_id: ClubId
    payload: Payload
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preview: str = Field(max_length=2000, description="what the approver sees, in plain words")
    risk: Risk
    proposed_by: Slug = Field(description="capability that proposed it")
    approver_roles: frozenset[Role] = Field(min_length=1)
    idempotency_key: Slug
    created_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        if self.payload_sha256 != payload_sha256(self.payload):
            raise ValueError("payload_sha256 does not match the payload")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        return self

    @property
    def kind(self) -> ActionKind:
        return self.payload.kind


class Decision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ApprovalDecision(Contract):
    action_id: Slug
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$", description="the payload the approver saw")
    decision: Decision
    actor: Actor
    decided_at: datetime
    reason: str | None = Field(default=None, max_length=300)


class ExecutionRecord(Contract):
    action_id: Slug
    idempotency_key: Slug
    executed_at: datetime
    executed_by: Literal["system"] = "system"
    external_ref: str | None = None
