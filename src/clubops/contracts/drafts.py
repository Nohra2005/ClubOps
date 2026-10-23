"""Planner -> drafter (Joey's templates). Every output is a draft: a person copies or sends it (D-41)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from clubops.contracts.common import ClubId, Contract, EventId, ItemId, Untrusted


class DraftType(StrEnum):
    WHATSAPP_ANNOUNCEMENT = "whatsapp_announcement"
    REMINDER_MESSAGE = "reminder_message"
    SPONSOR_EMAIL = "sponsor_email"
    INSTAGRAM_CAPTION = "instagram_caption"
    POSTER_TEXT = "poster_text"  # words only; logos are never drawn (D-07)
    EXPENSE_FORM = "expense_form"
    VOLUNTEER_SHIFTS = "volunteer_shifts"
    IMPACT_REPORT = "impact_report"


EMAIL_TYPES = frozenset({DraftType.SPONSOR_EMAIL})


class DraftRequest(Contract):
    club_id: ClubId
    event_id: EventId
    draft_type: DraftType
    instruction: Untrusted | None = Field(default=None, description="'what should change?' when rewriting a draft")


class Draft(Contract):
    event_id: EventId
    draft_type: DraftType
    template_version: str = Field(max_length=40, description="which template made it, for evaluation")
    subject: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    based_on: list[ItemId] = Field(default_factory=list, description="know-how the draft used")
    state: Literal["draft"] = "draft"

    @model_validator(mode="after")
    def _subject(self) -> Self:
        if (self.draft_type in EMAIL_TYPES) != (self.subject is not None):
            raise ValueError("emails have a subject; other drafts don't")
        return self
