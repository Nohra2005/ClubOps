"""The club's know-how: the spine of ClubOps.

Know-how is how things actually get done in the club: procedures, lessons, relationships,
gotchas, decisions and their reasons, the club's identity, its yearly rhythm, obligations,
and the AUB rules that apply. It is captured from untrusted sources, enters the knowledge
base only after a cabinet member verifies it, and is consumed by the event packet and by
the handover.

Write path:  capture (agentic) -> KnowHowProposal -> verify (human) -> KnowHowItem
Read path:   surface / ask / find_gaps (agentic, cite verified items only)
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from clubops.contracts.common import (
    ClubId,
    Contract,
    EventId,
    ItemId,
    MemberId,
    Role,
    Slug,
    SourceRef,
    Untrusted,
)

# ----------------------------------------------------------------------- enums


class Kind(StrEnum):
    PROCEDURE = "procedure"
    LESSON = "lesson"
    RELATIONSHIP = "relationship"
    GOTCHA = "gotcha"
    DECISION = "decision"
    IDENTITY = "identity"
    RHYTHM = "rhythm"
    OBLIGATION = "obligation"
    RULE = "rule"


class Scope(StrEnum):
    AUB = "aub"  # true for every club (e.g. an OSA rule)
    CLUB = "club"  # specific to one club


class ItemStatus(StrEnum):
    PROPOSED = "proposed"
    VERIFIED = "verified"
    DISPUTED = "disputed"  # an open contradiction exists
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class Visibility(StrEnum):
    CABINET = "cabinet"
    AUB_PUBLIC = "aub_public"


# --------------------------------------------------------------- kind details


class Step(Contract):
    order: int = Field(ge=1)
    action: str = Field(max_length=300)
    actor_role: Role | None = None
    channel: str | None = Field(default=None, max_length=80, description="email, webreserve form, in person...")
    lead_time_days: int | None = Field(default=None, ge=0, description="days before the event this must happen")


class ProcedureDetails(Contract):
    kind: Literal[Kind.PROCEDURE] = Kind.PROCEDURE
    goal: str = Field(max_length=200)
    steps: list[Step] = Field(min_length=1)
    applies_when: list[str] = Field(default_factory=list, description="tags such as 'green-field', 'prizes'")

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if [s.order for s in self.steps] != list(range(1, len(self.steps) + 1)):
            raise ValueError("steps must be numbered 1..n in order")
        return self


class LessonDetails(Contract):
    kind: Literal[Kind.LESSON] = Kind.LESSON
    outcome: Literal["worked", "failed", "mixed"]
    context: str = Field(max_length=500)
    recommendation: str = Field(max_length=500)


class RelationshipDetails(Contract):
    kind: Literal[Kind.RELATIONSHIP] = Kind.RELATIONSHIP
    party_name: str = Field(max_length=120)
    party_type: Literal["sponsor", "vendor", "aub_office", "venue", "other_club", "other"]
    offers: list[str] = Field(default_factory=list, description="sponsor categories or services, e.g. 'water'")
    preferred_channel: str | None = Field(default=None, max_length=80)
    contact_ref: str | None = Field(
        default=None, max_length=120, description="reference to a cabinet-only contact, never the raw number"
    )


class GotchaDetails(Contract):
    kind: Literal[Kind.GOTCHA] = Kind.GOTCHA
    trigger: str = Field(max_length=300)
    consequence: str = Field(max_length=300)
    avoid_by: str = Field(max_length=300)


class DecisionDetails(Contract):
    kind: Literal[Kind.DECISION] = Kind.DECISION
    decision: str = Field(max_length=300)
    rationale: str = Field(max_length=600)
    alternatives_considered: list[str] = Field(default_factory=list)
    decided_on: date | None = None


class IdentityDetails(Contract):
    kind: Literal[Kind.IDENTITY] = Kind.IDENTITY
    aspect: Literal["mission", "tone", "audience", "signature_event", "brand", "values"]


class RhythmDetails(Contract):
    kind: Literal[Kind.RHYTHM] = Kind.RHYTHM
    month: int = Field(ge=1, le=12)
    recurs: Literal["yearly", "fall", "spring"]


class ObligationDetails(Contract):
    kind: Literal[Kind.OBLIGATION] = Kind.OBLIGATION
    owed_to: str = Field(max_length=120, description="e.g. OSA")
    due_rule: str = Field(max_length=200, description="e.g. 'last week of each semester'")
    owner_role: Role | None = None


class RequirementKind(StrEnum):
    FORM = "form"
    APPROVAL = "approval"
    DOCUMENT = "document"
    LEAD_TIME = "lead_time"
    RESTRICTION = "restriction"


class Requirement(Contract):
    requirement_id: Slug
    kind: RequirementKind
    name: str = Field(max_length=200)
    detail: str | None = Field(default=None, max_length=500)
    lead_time_days: int | None = Field(default=None, ge=0)


class RuleDetails(Contract):
    kind: Literal[Kind.RULE] = Kind.RULE
    triggers: list[str] = Field(
        min_length=1,
        description="event facts that make the rule relevant, e.g. 'non_aub_guests', 'prizes', 'budget_over_threshold'",
    )
    requirements: list[Requirement] = Field(min_length=1)


Details = Annotated[
    ProcedureDetails
    | LessonDetails
    | RelationshipDetails
    | GotchaDetails
    | DecisionDetails
    | IdentityDetails
    | RhythmDetails
    | ObligationDetails
    | RuleDetails,
    Field(discriminator="kind"),
]

# ----------------------------------------------------------------------- items


class Support(Contract):
    """How well-supported an item is. Replaces an uncalibrated 'confidence' score."""

    events: list[EventId] = Field(default_factory=list)
    source_count: int = Field(ge=1)


class KnowHowItem(Contract):
    item_id: ItemId
    scope: Scope
    club_id: ClubId | None = Field(description="None only for AUB-scope items")
    title: str = Field(min_length=3, max_length=120)
    statement: str = Field(min_length=3, max_length=1500, description="the know-how in plain words")
    details: Details
    tags: list[Slug] = Field(default_factory=list)
    sources: list[SourceRef] = Field(min_length=1)
    support: Support
    stated_by_role: Role | None = None
    status: ItemStatus
    version: int = Field(ge=1)
    supersedes: ItemId | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    verified_by: MemberId | None = None
    verified_at: datetime | None = None
    last_confirmed_at: datetime | None = None
    visibility: Visibility = Visibility.CABINET

    @property
    def kind(self) -> Kind:
        return self.details.kind

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        if (self.scope is Scope.CLUB) != (self.club_id is not None):
            raise ValueError("club_id is required for club scope and forbidden for AUB scope")
        if self.status in (ItemStatus.VERIFIED, ItemStatus.SUPERSEDED) and not (self.verified_by and self.verified_at):
            raise ValueError("verified items name who verified them and when")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to precedes valid_from")
        if self.kind is Kind.RULE and self.scope is not Scope.AUB:
            raise ValueError("rules are AUB-scope; club conventions are procedures or decisions")
        if self.support.source_count < len({(s.kind, s.source_id) for s in self.sources}):
            raise ValueError("support.source_count is lower than the number of distinct sources")
        return self

    def is_current(self, on: date) -> bool:
        return (
            self.status is ItemStatus.VERIFIED
            and (self.valid_from is None or self.valid_from <= on)
            and (self.valid_to is None or on <= self.valid_to)
        )


# ---------------------------------------------------------------- write path


class CaptureRequest(Contract):
    """Ask the agent to extract know-how from raw material."""

    club_id: ClubId
    sources: list[Untrusted] = Field(min_length=1, max_length=200)
    context_event: EventId | None = None


class ProposalOp(StrEnum):
    CREATE = "create"
    MERGE = "merge"  # same know-how as an existing item; adds support
    UPDATE = "update"  # replaces an existing item with a new version
    RETIRE = "retire"  # an existing item is no longer true
    CONTRADICTION = "contradiction"  # conflicts with an existing item; a human must decide


class KnowHowProposal(Contract):
    proposal_id: Slug
    op: ProposalOp
    candidate: KnowHowItem
    target_item: ItemId | None = None
    conflicts_with: list[ItemId] = Field(default_factory=list)
    rationale: str = Field(max_length=600)
    redactions: list[Literal["phone", "aub_id", "email", "personal_name", "other_pii"]] = Field(default_factory=list)
    injection_flags: list[str] = Field(default_factory=list, description="suspicious instructions found in the source")

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        if self.candidate.status is not ItemStatus.PROPOSED:
            raise ValueError("a proposal's candidate must have status 'proposed'")
        if self.op is not ProposalOp.CREATE and self.target_item is None:
            raise ValueError(f"op '{self.op}' needs target_item")
        if self.op is ProposalOp.CONTRADICTION and not self.conflicts_with:
            raise ValueError("a contradiction names the items it conflicts with")
        if not any(s.quote for s in self.candidate.sources):
            raise ValueError("a proposal quotes at least one source")
        return self


class CaptureResult(Contract):
    proposals: list[KnowHowProposal]
    sources_seen: int = Field(ge=0)
    sources_skipped: int = Field(ge=0, description="e.g. off-topic or flagged as injection")


class VerifyDecision(StrEnum):
    ACCEPT = "accept"
    ACCEPT_EDITED = "accept_edited"
    REJECT = "reject"


class VerifyRequest(Contract):
    """Human-only. The agent can never call this on its own behalf."""

    proposal: KnowHowProposal
    decision: VerifyDecision
    edited_candidate: KnowHowItem | None = None
    reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _edited(self) -> Self:
        if (self.decision is VerifyDecision.ACCEPT_EDITED) != (self.edited_candidate is not None):
            raise ValueError("edited_candidate is given exactly when decision is accept_edited")
        return self


class VerifyResult(Contract):
    committed: KnowHowItem | None
    superseded: list[ItemId] = Field(default_factory=list)


# ----------------------------------------------------------------- read path


class Situation(Contract):
    """What the cabinet is about to do, used to surface relevant know-how."""

    summary: str = Field(max_length=500)
    event: EventId | None = None
    tags: list[Slug] = Field(default_factory=list)
    on: date


class SurfaceRequest(Contract):
    club_id: ClubId
    situation: Situation
    limit: int = Field(default=8, ge=1, le=30)


class SurfacedItem(Contract):
    item_id: ItemId
    kind: Kind
    title: str
    why_relevant: str = Field(max_length=300)
    disputed: bool = False


class SurfaceResult(Contract):
    items: list[SurfacedItem]


class AskRequest(Contract):
    club_id: ClubId
    question: str = Field(min_length=3, max_length=500)
    as_of: date


class Answer(Contract):
    known: bool
    text: str = Field(max_length=1500)
    citations: list[ItemId] = Field(default_factory=list)
    basis: Literal["verified", "single_source", "disputed", "none"]

    @model_validator(mode="after")
    def _cited(self) -> Self:
        if self.known and not self.citations:
            raise ValueError("a known answer cites at least one verified item")
        if not self.known and (self.citations or self.basis != "none"):
            raise ValueError("an unknown answer has no citations and basis 'none'")
        return self


class GapKind(StrEnum):
    MISSING = "missing"  # e.g. a sponsor with no contact route
    STALE = "stale"  # not confirmed for too long
    UNVERIFIED = "unverified"  # proposed but nobody verified it
    CONTRADICTION = "contradiction"
    UNOWNED_OBLIGATION = "unowned_obligation"


class Gap(Contract):
    gap_id: Slug
    kind: GapKind
    about: ItemId | None = None
    topic: str = Field(max_length=200)
    question: str = Field(max_length=400, description="what to ask the outgoing officer")
    priority: Literal["high", "medium", "low"]


class GapRequest(Contract):
    club_id: ClubId
    role: Role | None = None
    as_of: date
    stale_after_days: int = Field(default=365, ge=30)


class GapReport(Contract):
    gaps: list[Gap]
