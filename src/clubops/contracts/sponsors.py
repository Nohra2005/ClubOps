"""Sponsor needs per event, and gap-based replacement. PROVISIONAL (v0): may change in Phase 2.

Candidates come only from verified RELATIONSHIP know-how, never from the open web.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from clubops.contracts.common import ClubId, Contract, EventId, ItemId, Slug, SourceRef


class NeedStatus(StrEnum):
    OPEN = "open"
    PITCHED = "pitched"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CANCELLED = "cancelled"


# Deterministic state machine for a sponsor need.
ALLOWED_TRANSITIONS: dict[NeedStatus, frozenset[NeedStatus]] = {
    NeedStatus.OPEN: frozenset({NeedStatus.PITCHED}),
    NeedStatus.PITCHED: frozenset({NeedStatus.CONFIRMED, NeedStatus.DECLINED}),
    NeedStatus.CONFIRMED: frozenset({NeedStatus.CANCELLED}),
    NeedStatus.DECLINED: frozenset({NeedStatus.OPEN}),
    NeedStatus.CANCELLED: frozenset({NeedStatus.OPEN}),
}


class SponsorNeed(Contract):
    need_id: Slug
    event_id: EventId
    category: Slug = Field(description="e.g. 'water', 'prizes', 'printing'")
    description: str = Field(max_length=300)
    status: NeedStatus
    sponsor: ItemId | None = Field(default=None, description="RELATIONSHIP item currently filling the need")
    confirmation: SourceRef | None = Field(default=None, description="the email or message confirming it (form Q31)")


class ReplacementRequest(Contract):
    club_id: ClubId
    need: SponsorNeed
    exclude: list[ItemId] = Field(default_factory=list, description="already asked or declined")


class Candidate(Contract):
    sponsor: ItemId
    why: str = Field(max_length=300)
    past_events: list[EventId] = Field(default_factory=list)


class ReplacementSuggestions(Contract):
    need_id: Slug
    candidates: list[Candidate] = Field(max_length=5)
