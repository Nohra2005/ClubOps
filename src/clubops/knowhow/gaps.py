"""Deterministic gap checks. These are also the declared fallback of the agentic find-gaps."""

from __future__ import annotations

from datetime import timedelta

from clubops.contracts.common import Role
from clubops.contracts.knowhow import (
    Gap,
    GapKind,
    GapReport,
    GapRequest,
    KnowHowItem,
    ObligationDetails,
    ProcedureDetails,
    ProposalOp,
    RelationshipDetails,
)
from clubops.knowhow.store import KnowHowStore

LEADERSHIP = frozenset({Role.PRESIDENT, Role.VICE_PRESIDENT})


def relevant_to(item: KnowHowItem, role: Role | None) -> bool:
    """Which items belong in a role's handover. Leadership sees everything."""
    if role is None or role in LEADERSHIP:
        return True
    details = item.details
    if item.stated_by_role is role or role.value in item.tags:
        return True
    if isinstance(details, ProcedureDetails):
        return any(step.actor_role is role for step in details.steps)
    if isinstance(details, ObligationDetails):
        return details.owner_role is role
    if isinstance(details, RelationshipDetails):
        return role is Role.SPONSORSHIP and details.party_type == "sponsor"
    return item.kind.value in {"identity", "rule"}


def deterministic_gaps(store: KnowHowStore, request: GapRequest) -> GapReport:
    gaps: list[Gap] = []
    stale_before = request.as_of - timedelta(days=request.stale_after_days)

    for item in store.current(request.club_id, request.as_of):
        if not relevant_to(item, request.role):
            continue
        confirmed = item.last_confirmed_at or item.verified_at
        if confirmed is not None and confirmed.date() < stale_before:
            gaps.append(
                Gap(
                    gap_id=f"stale-{item.item_id}",
                    kind=GapKind.STALE,
                    about=item.item_id,
                    topic=item.title,
                    question=f'Is this still true: "{item.statement[:200]}"?',
                    priority="medium",
                )
            )
        details = item.details
        if isinstance(details, ObligationDetails) and details.owner_role is None:
            gaps.append(
                Gap(
                    gap_id=f"owner-{item.item_id}",
                    kind=GapKind.UNOWNED_OBLIGATION,
                    about=item.item_id,
                    topic=item.title,
                    question=f"Which role is responsible for '{item.title}'?",
                    priority="high",
                )
            )
        if isinstance(details, RelationshipDetails) and not (details.contact_ref or details.preferred_channel):
            gaps.append(
                Gap(
                    gap_id=f"contact-{item.item_id}",
                    kind=GapKind.MISSING,
                    about=item.item_id,
                    topic=details.party_name,
                    question=f"How does the club reach {details.party_name}, and through whom?",
                    priority="high",
                )
            )

    for proposal in store.pending.values():
        if proposal.candidate.club_id not in (None, request.club_id) or not relevant_to(
            proposal.candidate, request.role
        ):
            continue
        kind = GapKind.CONTRADICTION if proposal.op is ProposalOp.CONTRADICTION else GapKind.UNVERIFIED
        gaps.append(
            Gap(
                gap_id=f"pending-{proposal.proposal_id}",
                kind=kind,
                about=proposal.target_item,
                topic=proposal.candidate.title,
                question=f'Should this be recorded as club know-how: "{proposal.candidate.statement[:200]}"?',
                priority="high" if kind is GapKind.CONTRADICTION else "low",
            )
        )

    order = {"high": 0, "medium": 1, "low": 2}
    return GapReport(gaps=sorted(gaps, key=lambda g: (order[g.priority], g.gap_id)))
