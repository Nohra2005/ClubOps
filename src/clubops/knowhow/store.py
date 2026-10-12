"""In-memory knowledge base with the verified-write rule built in.

Proposals wait in ``pending`` until a cabinet member verifies them. Nothing else writes items.
History is kept: an updated item keeps its old versions, marked superseded.
A SQLite implementation will replace this behind the same methods (docs/adr/0004).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from clubops.capabilities.runner import CapabilityError, Outcome
from clubops.contracts.common import Actor, ClubId, ErrorCode, ItemId, Role
from clubops.contracts.knowhow import (
    ItemStatus,
    Kind,
    KnowHowItem,
    KnowHowProposal,
    ProposalOp,
    Scope,
    Support,
    VerifyDecision,
    VerifyRequest,
    VerifyResult,
)


def _rebuild(item: KnowHowItem, **changes: Any) -> KnowHowItem:
    """Copy with changes, re-running every invariant (model_copy would skip them)."""
    return KnowHowItem.model_validate({**item.model_dump(), **changes})


class KnowHowStore:
    def __init__(self) -> None:
        self._versions: dict[ItemId, list[KnowHowItem]] = {}
        self.pending: dict[str, KnowHowProposal] = {}

    # ------------------------------------------------------------------ reads

    def latest(self, item_id: ItemId) -> KnowHowItem | None:
        versions = self._versions.get(item_id)
        return versions[-1] if versions else None

    def history(self, item_id: ItemId) -> list[KnowHowItem]:
        return list(self._versions.get(item_id, []))

    def visible(self, club_id: ClubId) -> list[KnowHowItem]:
        return [v[-1] for v in self._versions.values() if v[-1].scope is Scope.AUB or v[-1].club_id == club_id]

    def current(self, club_id: ClubId, on: date, kinds: Iterable[Kind] | None = None) -> list[KnowHowItem]:
        wanted = set(kinds) if kinds is not None else None
        return sorted(
            (i for i in self.visible(club_id) if i.is_current(on) and (wanted is None or i.kind in wanted)),
            key=lambda i: i.item_id,
        )

    # ----------------------------------------------------------------- writes

    def submit(self, proposal: KnowHowProposal) -> None:
        self.pending[proposal.proposal_id] = proposal

    def verify(self, request: VerifyRequest, actor: Actor, now: datetime) -> Outcome[VerifyResult]:
        proposal = request.proposal
        if proposal.proposal_id not in self.pending:
            raise CapabilityError(ErrorCode.NOT_FOUND, "no pending proposal with this id")
        if not actor.is_cabinet:
            raise CapabilityError(ErrorCode.NOT_AUTHORIZED, "only verified cabinet members verify know-how")
        candidate = request.edited_candidate or proposal.candidate
        if candidate.scope is Scope.CLUB and candidate.club_id != actor.club_id:
            raise CapabilityError(ErrorCode.NOT_AUTHORIZED, "cannot verify another club's know-how")
        if candidate.scope is Scope.AUB and Role.PRESIDENT not in actor.roles:
            raise CapabilityError(ErrorCode.NOT_AUTHORIZED, "AUB-wide rules are verified by a club president")
        if proposal.injection_flags and request.decision is not VerifyDecision.REJECT and not request.reason:
            raise CapabilityError(
                ErrorCode.INJECTION_SUSPECTED, "accepting a flagged proposal requires a written reason"
            )

        del self.pending[proposal.proposal_id]
        if request.decision is VerifyDecision.REJECT:
            return Outcome(data=VerifyResult(committed=None))

        stamp = {
            "status": ItemStatus.VERIFIED,
            "verified_by": actor.member_id,
            "verified_at": now,
            "last_confirmed_at": now,
        }
        target = self.latest(proposal.target_item) if proposal.target_item else None
        if proposal.op is not ProposalOp.CREATE and target is None:
            raise CapabilityError(ErrorCode.NOT_FOUND, "the proposal's target item does not exist")

        superseded: list[ItemId] = []
        match proposal.op:
            case ProposalOp.CREATE:
                if candidate.item_id in self._versions:
                    raise CapabilityError(ErrorCode.CONFLICT, "an item with this id already exists")
                committed = _rebuild(candidate, version=1, **stamp)
            case ProposalOp.UPDATE if target is not None:
                committed = _rebuild(candidate, item_id=target.item_id, version=target.version + 1, **stamp)
                self._mark_superseded(target.item_id)
            case ProposalOp.MERGE if target is not None:
                sources = list(
                    {(s.kind, s.source_id, s.locator): s for s in [*target.sources, *candidate.sources]}.values()
                )
                support = Support(
                    events=sorted({*target.support.events, *candidate.support.events}),
                    source_count=max(len(sources), target.support.source_count),
                )
                committed = _rebuild(target, sources=sources, support=support, version=target.version + 1, **stamp)
                self._mark_superseded(target.item_id)
            case ProposalOp.RETIRE if target is not None:
                committed = _rebuild(
                    target,
                    status=ItemStatus.RETIRED,
                    version=target.version + 1,
                    valid_to=now.date(),
                    verified_by=actor.member_id,
                    verified_at=now,
                )
                self._mark_superseded(target.item_id)
            case ProposalOp.CONTRADICTION:
                # Accepting a contradiction means the candidate wins over the items it conflicts with.
                committed = _rebuild(candidate, version=1, supersedes=proposal.target_item, **stamp)
                for loser in proposal.conflicts_with:
                    if self.latest(loser) is not None:
                        self._mark_superseded(loser)
                        superseded.append(loser)
            case _:
                raise CapabilityError(ErrorCode.INTERNAL, f"unhandled proposal op {proposal.op}")

        if proposal.op in (ProposalOp.UPDATE, ProposalOp.MERGE, ProposalOp.RETIRE):
            superseded.append(committed.item_id)
        self._versions.setdefault(committed.item_id, []).append(committed)
        return Outcome(data=VerifyResult(committed=committed, superseded=superseded))

    def _mark_superseded(self, item_id: ItemId) -> None:
        versions = self._versions[item_id]
        if versions[-1].status is ItemStatus.VERIFIED:
            versions[-1] = _rebuild(versions[-1], status=ItemStatus.SUPERSEDED)
