"""Handover: passing a role's know-how from the outgoing officer to the incoming one.

Flow:  find_gaps -> interview (outgoing officer answers; answers go through capture/verify)
       -> build_handover (every line cites verified know-how) -> sign-off (human)
       -> role transfer (approval-gated action)
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from clubops.contracts.common import ClubId, Contract, ItemId, MemberId, Role, Slug
from clubops.contracts.knowhow import Gap


class HandoverRequest(Contract):
    club_id: ClubId
    role: Role
    outgoing: MemberId
    incoming: MemberId | None = None
    as_of: date


class InterviewQuestion(Contract):
    gap_id: Slug
    text: str = Field(max_length=400)
    why: str = Field(max_length=300, description="why the agent is asking, shown to the officer")


class InterviewRequest(Contract):
    club_id: ClubId
    role: Role
    gaps: list[Gap] = Field(min_length=1)
    max_questions: int = Field(default=12, ge=1, le=25)


class Interview(Contract):
    """Questions for the outgoing officer. Answers are captured as SourceKind.INTERVIEW."""

    club_id: ClubId
    role: Role
    questions: list[InterviewQuestion] = Field(max_length=25)


class Section(StrEnum):
    OPEN_OBLIGATIONS = "open_obligations"
    YEAR_AT_A_GLANCE = "year_at_a_glance"
    PROCEDURES = "procedures"
    RELATIONSHIPS = "relationships"
    LESSONS = "lessons"
    DECISIONS = "decisions"
    IDENTITY = "identity"
    RULES = "rules"
    OPEN_QUESTIONS = "open_questions"


class HandoverEntry(Contract):
    text: str = Field(min_length=3, max_length=600)
    item_ids: list[ItemId] = Field(default_factory=list)
    gap_ids: list[Slug] = Field(default_factory=list)
    last_confirmed: date | None = None

    @model_validator(mode="after")
    def _cited(self) -> Self:
        if not (self.item_ids or self.gap_ids):
            raise ValueError("every handover entry cites a verified item or an open gap")
        return self


class HandoverSection(Contract):
    section: Section
    entries: list[HandoverEntry]


class PackStatus(StrEnum):
    DRAFT = "draft"
    SIGNED_OFF = "signed_off"


class HandoverPack(Contract):
    pack_id: Slug
    club_id: ClubId
    role: Role
    as_of: date
    version: int = Field(ge=1)
    sections: list[HandoverSection]
    open_gaps: list[Gap] = Field(default_factory=list)
    status: PackStatus = PackStatus.DRAFT
    signed_off_by: MemberId | None = None
    signed_off_at: datetime | None = None

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        seen = [s.section for s in self.sections]
        if len(seen) != len(set(seen)):
            raise ValueError("each section appears at most once")
        if (self.status is PackStatus.SIGNED_OFF) != bool(self.signed_off_by and self.signed_off_at):
            raise ValueError("signed-off packs name who signed and when; drafts do not")
        return self

    def content_sha256(self) -> str:
        """Hash of the content a sign-off approves. Any edit invalidates the sign-off."""
        body = self.model_dump_json(include={"club_id", "role", "as_of", "version", "sections", "open_gaps"})
        return hashlib.sha256(body.encode()).hexdigest()


class HandoverQuestion(Contract):
    """One of the standard questions used to test a handover (evaluation)."""

    question_id: Slug
    role: Role
    text: str = Field(max_length=300)
    expected: str = Field(max_length=600, description="answer given by the outgoing cabinet")
    category: Literal["sponsors", "procedures", "deadlines", "rules", "contacts", "lessons", "identity"]
