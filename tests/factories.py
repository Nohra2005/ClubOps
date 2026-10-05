"""Builders for synthetic test data. Nothing here is real club data."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from clubops.contracts.common import Actor, Role, SourceKind, SourceRef
from clubops.contracts.knowhow import (
    ItemStatus,
    KnowHowItem,
    KnowHowProposal,
    ProposalOp,
    Requirement,
    RequirementKind,
    RuleDetails,
    Scope,
    Support,
)

CLUB = "running-club"
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
TODAY = date(2026, 10, 5)


def actor(*roles: Role, verified: bool = True, club: str = CLUB, member: str = "m-tester") -> Actor:
    return Actor(member_id=member, club_id=club, roles=frozenset(roles or {Role.PRESIDENT}), verified=verified)


def source(sid: str = "synthetic-chat-1", quote: str | None = "we always book three weeks ahead") -> SourceRef:
    return SourceRef(kind=SourceKind.CHAT_MESSAGE, source_id=sid, quote=quote, observed_at=NOW)


def item(item_id: str = "kh-book-green-field", **overrides: Any) -> KnowHowItem:
    data: dict[str, Any] = {
        "item_id": item_id,
        "scope": Scope.CLUB,
        "club_id": CLUB,
        "title": "Booking Green Field",
        "statement": "Book Green Field three weeks ahead through the facility reservation form.",
        "details": {
            "kind": "procedure",
            "goal": "Reserve Green Field for an event",
            "steps": [
                {
                    "order": 1,
                    "action": "Submit the facility reservation form",
                    "actor_role": "events",
                    "lead_time_days": 21,
                }
            ],
            "applies_when": ["green-field"],
        },
        "tags": ["green-field"],
        "sources": [source()],
        "support": {"events": [], "source_count": 1},
        "status": ItemStatus.PROPOSED,
        "version": 1,
    }
    data.update(overrides)
    return KnowHowItem.model_validate(data)


def rule(item_id: str = "kh-rule-guests", *reqs: Requirement, **overrides: Any) -> KnowHowItem:
    requirements = list(reqs) or [
        Requirement(
            requirement_id="guest-approval",
            kind=RequirementKind.APPROVAL,
            name="OSA approval for non-AUB guests",
            lead_time_days=14,
        )
    ]
    return item(
        item_id,
        scope=Scope.AUB,
        club_id=None,
        title="Non-AUB guests need approval",
        statement="Events open to non-AUB guests need OSA approval.",
        details=RuleDetails(triggers=["non_aub_guests"], requirements=requirements),
        tags=["guests"],
        **overrides,
    )


def proposal(
    candidate: KnowHowItem | None = None, op: ProposalOp = ProposalOp.CREATE, pid: str = "p-1", **kw: Any
) -> KnowHowProposal:
    return KnowHowProposal(proposal_id=pid, op=op, candidate=candidate or item(), rationale="synthetic", **kw)


def verified(it: KnowHowItem, by: str = "m-tester") -> KnowHowItem:
    return KnowHowItem.model_validate(
        {**it.model_dump(), "status": ItemStatus.VERIFIED, "verified_by": by, "verified_at": NOW}
    )


__all__ = ["CLUB", "NOW", "TODAY", "Support", "actor", "item", "proposal", "rule", "source", "verified"]
