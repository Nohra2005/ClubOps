"""The knowledge base, with the verified-write rule built in.

Proposals wait in ``pending`` until a cabinet member verifies them. Nothing else writes items.
History is kept: an updated item keeps its old versions, marked superseded.
Where the data lives is a backend's job (memory, or SQLite files: ``backends.py``, ADR 0004);
every rule is here, so all backends behave the same.
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
from clubops.knowhow.backends import Backend, MemoryBackend


def _rebuild(item: KnowHowItem, **changes: Any) -> KnowHowItem:
    """Copy with changes, re-running every invariant (model_copy would skip them)."""
    return KnowHowItem.model_validate({**item.model_dump(), **changes})


def rescoped(item: KnowHowItem, club_id: ClubId, *, shared: bool) -> KnowHowItem:
    """The same fact for every AUB club (``shared``) or for ``club_id`` only. A president decides (D-91)."""
    if shared:
        return _rebuild(item, scope=Scope.AUB, club_id=None)
    return _rebuild(item, scope=Scope.CLUB, club_id=club_id)


class KnowHowStore:
    def __init__(self, backend: Backend | None = None) -> None:
        self.backend: Backend = backend if backend is not None else MemoryBackend()

    def close(self) -> None:
        self.backend.close()

    # ------------------------------------------------------------------ reads

    @property
    def pending(self) -> dict[str, KnowHowProposal]:
        """Proposals waiting for a cabinet member's decision (a snapshot; change it through submit/verify)."""
        return self.backend.pending_all()

    def latest(self, item_id: ItemId) -> KnowHowItem | None:
        versions = self.backend.versions(item_id)
        return versions[-1] if versions else None

    def history(self, item_id: ItemId) -> list[KnowHowItem]:
        return self.backend.versions(item_id)

    def visible(self, club_id: ClubId) -> list[KnowHowItem]:
        return [i for i in self.backend.latest_all() if i.scope is Scope.AUB or i.club_id == club_id]

    def search(self, club_id: ClubId, text: str, limit: int = 10) -> list[KnowHowItem]:
        """Approved items this club may see, best match first (plain full-text search, no model)."""
        found: list[KnowHowItem] = []
        for item_id, _score in self.backend.search(text, limit * 3):
            item = self.latest(item_id)
            if (
                item is not None
                and item.status in (ItemStatus.VERIFIED, ItemStatus.DISPUTED)
                and (item.scope is Scope.AUB or item.club_id == club_id)
            ):
                found.append(item)
            if len(found) == limit:
                break
        return found

    def current(self, club_id: ClubId, on: date, kinds: Iterable[Kind] | None = None) -> list[KnowHowItem]:
        wanted = set(kinds) if kinds is not None else None
        return sorted(
            (i for i in self.visible(club_id) if i.is_current(on) and (wanted is None or i.kind in wanted)),
            key=lambda i: i.item_id,
        )

    # ----------------------------------------------------------------- writes

    def submit(self, proposal: KnowHowProposal) -> None:
        self.backend.pending_put(proposal)

    def verify(self, request: VerifyRequest, actor: Actor, now: datetime) -> Outcome[VerifyResult]:
        """Apply a cabinet member's decision to a queued proposal.

        The queued copy is the only one trusted: a request carrying different content under the
        same id (a stale screen, or a tampered request that drops injection flags) is refused.
        Every check runs before anything changes, so a refused decision leaves the proposal queued.
        Changing the content is only possible through ``accept_edited``, which is explicit.
        """
        proposal, candidate = self._checked(request, actor)
        if request.decision is VerifyDecision.REJECT:
            self.backend.pending_delete(proposal.proposal_id)
            return Outcome(data=VerifyResult(committed=None))

        committed, to_supersede = self._next_version(proposal, candidate, actor, now)
        with self.backend.transaction():
            for item_id in to_supersede:
                self._mark_superseded(item_id)
            self.backend.append(committed)
            self.backend.pending_delete(proposal.proposal_id)
        return Outcome(data=VerifyResult(committed=committed, superseded=to_supersede))

    def keep_both(
        self, proposal_id: str, edited: KnowHowItem | None, reason: str | None, actor: Actor, now: datetime
    ) -> KnowHowItem:
        """Approve a proposal as a new fact next to the known one, which stays as it is. Same checks as ``verify``."""
        queued = self.backend.pending_all().get(proposal_id)
        if queued is None:
            raise CapabilityError(ErrorCode.NOT_FOUND, "no pending proposal with this id")
        proposal, candidate = self._checked(
            VerifyRequest(
                proposal=queued,
                decision=VerifyDecision.ACCEPT_EDITED if edited is not None else VerifyDecision.ACCEPT,
                edited_candidate=edited,
                reason=reason,
            ),
            actor,
        )
        if self.backend.has(candidate.item_id):
            raise CapabilityError(ErrorCode.CONFLICT, "an item with this id already exists")
        committed = _rebuild(
            candidate,
            version=1,
            status=ItemStatus.VERIFIED,
            verified_by=actor.member_id,
            verified_at=now,
            last_confirmed_at=now,
        )
        with self.backend.transaction():
            self.backend.append(committed)
            self.backend.pending_delete(proposal.proposal_id)
        return committed

    def _checked(self, request: VerifyRequest, actor: Actor) -> tuple[KnowHowProposal, KnowHowItem]:
        """Every refusal happens here, before the store changes."""
        proposal = self.backend.pending_all().get(request.proposal.proposal_id)
        if proposal is None:
            raise CapabilityError(ErrorCode.NOT_FOUND, "no pending proposal with this id")
        if request.proposal != proposal:
            raise CapabilityError(
                ErrorCode.STALE_INPUT, "the proposal differs from the queued one; reload it and decide again"
            )
        if not actor.is_cabinet:
            raise CapabilityError(ErrorCode.NOT_AUTHORIZED, "only verified cabinet members verify know-how")
        candidate = request.edited_candidate or proposal.candidate
        if candidate.scope is Scope.CLUB and candidate.club_id != actor.club_id:
            raise CapabilityError(ErrorCode.NOT_AUTHORIZED, "cannot verify another club's know-how")
        target = self.latest(proposal.target_item) if proposal.target_item else None
        shared = candidate.scope is Scope.AUB or (target is not None and target.scope is Scope.AUB)
        if shared and Role.PRESIDENT not in actor.roles:
            raise CapabilityError(ErrorCode.NOT_AUTHORIZED, "AUB-wide facts are verified by a club president")
        if proposal.injection_flags and request.decision is not VerifyDecision.REJECT and not request.reason:
            raise CapabilityError(
                ErrorCode.INJECTION_SUSPECTED, "accepting a flagged proposal requires a written reason"
            )
        return proposal, candidate

    def _next_version(
        self, proposal: KnowHowProposal, candidate: KnowHowItem, actor: Actor, now: datetime
    ) -> tuple[KnowHowItem, list[ItemId]]:
        """The item to commit and the items it supersedes. Reads only; the caller writes."""
        stamp = {
            "status": ItemStatus.VERIFIED,
            "verified_by": actor.member_id,
            "verified_at": now,
            "last_confirmed_at": now,
        }
        target = self.latest(proposal.target_item) if proposal.target_item else None
        if proposal.op is not ProposalOp.CREATE and target is None:
            raise CapabilityError(ErrorCode.NOT_FOUND, "the proposal's target item does not exist")

        match proposal.op:
            case ProposalOp.CREATE:
                if self.backend.has(candidate.item_id):
                    raise CapabilityError(ErrorCode.CONFLICT, "an item with this id already exists")
                return _rebuild(candidate, version=1, **stamp), []
            case ProposalOp.UPDATE if target is not None:
                # A new version stays in its fact's layer: a club can't pull an AUB fact into its own (F-163).
                committed = _rebuild(
                    candidate,
                    item_id=target.item_id,
                    version=target.version + 1,
                    scope=target.scope,
                    club_id=target.club_id,
                    **stamp,
                )
                return committed, [target.item_id]
            case ProposalOp.MERGE if target is not None:
                sources = list(
                    {(s.kind, s.source_id, s.locator): s for s in [*target.sources, *candidate.sources]}.values()
                )
                support = Support(
                    events=sorted({*target.support.events, *candidate.support.events}),
                    source_count=max(len(sources), target.support.source_count),
                )
                committed = _rebuild(target, sources=sources, support=support, version=target.version + 1, **stamp)
                return committed, [target.item_id]
            case ProposalOp.RETIRE if target is not None:
                committed = _rebuild(
                    target,
                    status=ItemStatus.RETIRED,
                    version=target.version + 1,
                    valid_to=now.date(),
                    verified_by=actor.member_id,
                    verified_at=now,
                )
                return committed, [target.item_id]
            case ProposalOp.CONTRADICTION:
                # Accepting a contradiction means the candidate wins over the items it conflicts with.
                losers = [loser for loser in proposal.conflicts_with if self.latest(loser) is not None]
                existing = self.latest(candidate.item_id)
                if existing is None:
                    return _rebuild(candidate, version=1, supersedes=proposal.target_item, **stamp), losers
                if candidate.item_id in losers:
                    # The winner keeps the loser's id: it is that item's next version, not a second version 1.
                    return _rebuild(candidate, version=existing.version + 1, supersedes=None, **stamp), losers
                raise CapabilityError(
                    ErrorCode.CONFLICT, "the winning item reuses the id of an item it does not conflict with"
                )
            case _:
                raise CapabilityError(ErrorCode.INTERNAL, f"unhandled proposal op {proposal.op}")

    def restore(self, item_id: ItemId, actor: Actor, now: datetime, valid_to: date | None) -> KnowHowItem:
        """Bring an expired item back from the archive with a new end date (or none) as its next version.

        Expiry is a plain date rule: once ``valid_to`` has passed, the planner no longer uses the item
        (``current``), and it stays stored as history. A person restores it when the guessed date was
        wrong (D-115). Nothing else about the item changes."""
        item = self.latest(item_id)
        if item is None or (item.scope is Scope.CLUB and item.club_id != actor.club_id):
            raise CapabilityError(ErrorCode.NOT_FOUND, "no such item for this club")
        if item.scope is not Scope.CLUB:
            # An AUB-wide fact is shared by every club: one club's president may not republish it (D-115).
            raise CapabilityError(ErrorCode.NOT_AUTHORIZED, "AUB-wide facts are restored by the ClubOps operator")
        if item.status is not ItemStatus.VERIFIED or item.valid_to is None or item.valid_to >= now.date():
            raise CapabilityError(ErrorCode.CONFLICT, "only an approved item whose end date has passed can be restored")
        if valid_to is not None and valid_to < now.date():
            raise CapabilityError(ErrorCode.INVALID_INPUT, "the new end date is already in the past")
        restored = _rebuild(
            item,
            version=item.version + 1,
            valid_to=valid_to,
            verified_by=actor.member_id,
            verified_at=now,
        )
        with self.backend.transaction():
            self._mark_superseded(item_id)
            self.backend.append(restored)
        return restored

    def _mark_superseded(self, item_id: ItemId) -> None:
        latest = self.latest(item_id)
        if latest is not None and latest.status is ItemStatus.VERIFIED:
            self.backend.replace_latest(_rebuild(latest, status=ItemStatus.SUPERSEDED))
