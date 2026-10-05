"""Which AUB rules apply to an event, and what they require.

The model decides applicability (with reasons and the facts it used). Code derives the
requirements, so the requirement list is reproducible from the verdicts.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from clubops.contracts.common import Contract, EventId, FieldPath, ItemId
from clubops.contracts.event import EventSpec
from clubops.contracts.knowhow import Requirement


class RuleApplicationRequest(Contract):
    spec: EventSpec
    as_of: date


class Applicability(StrEnum):
    APPLIES = "applies"
    NOT_APPLICABLE = "not_applicable"
    UNCERTAIN = "uncertain"


class RuleVerdict(Contract):
    item_id: ItemId
    item_version: int = Field(ge=1)
    verdict: Applicability
    reason: str = Field(max_length=400)
    facts_used: list[FieldPath] = Field(default_factory=list)

    @model_validator(mode="after")
    def _facts(self) -> Self:
        if self.verdict is not Applicability.UNCERTAIN and not self.facts_used:
            raise ValueError("a definite verdict names the event facts it relied on")
        return self


class DerivedRequirement(Contract):
    requirement: Requirement
    from_items: list[ItemId] = Field(min_length=1)
    uncertain: bool = Field(description="True when only UNCERTAIN verdicts support it")


class RuleApplication(Contract):
    event_id: EventId
    spec_revision: int = Field(ge=1)
    rulebook: list[tuple[ItemId, int]] = Field(description="(item, version) of every rule considered")
    verdicts: list[RuleVerdict]
    requirements: list[DerivedRequirement]

    @model_validator(mode="after")
    def _covers_rulebook(self) -> Self:
        judged = {(v.item_id, v.item_version) for v in self.verdicts}
        if judged != set(self.rulebook):
            raise ValueError("every rule in the rulebook snapshot gets exactly one verdict")
        if len(judged) != len(self.verdicts):
            raise ValueError("duplicate verdicts")
        return self
