"""OSA forms as versioned data, and drafts of answers to them.

The form definition lives in data/forms/*.json. Validators read it, so when OSA changes
the form for next year only the JSON changes.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from clubops.contracts.club import ClubProfile, RequesterDetails
from clubops.contracts.common import Contract, EventId, Origin, SourceRef
from clubops.contracts.event import EventSpec
from clubops.contracts.rules import RuleApplication

FormFieldId = Annotated[str, StringConstraints(pattern=r"^q\d{2}$")]


class FieldType(StrEnum):
    TEXT = "text"
    LONG_TEXT = "long_text"
    EMAIL = "email"
    PHONE = "phone"
    AUB_ID = "aub_id"
    DATE = "date"
    TIME_24H = "time_24h"
    COUNT_RANGE = "count_range"
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    FILE = "file"


class RequiredIf(Contract):
    field_id: FormFieldId
    equals: str


class FormField(Contract):
    field_id: FormFieldId
    label: str = Field(max_length=400)
    help: str | None = Field(default=None, max_length=400)
    type: FieldType
    required: bool
    required_if: RequiredIf | None = None
    choices: list[str] = Field(default_factory=list)
    max_files: int | None = Field(default=None, ge=1)
    sensitive: bool = False
    source: str = Field(
        pattern=r"^((event|profile|requester|attachment)\.[a-z_.]+|human)$",
        description="where the answer comes from: event.*, profile.*, requester.*, attachment.* or human",
    )

    @model_validator(mode="after")
    def _shape(self) -> Self:
        choice = self.type in (FieldType.SINGLE_CHOICE, FieldType.MULTI_CHOICE)
        if choice != bool(self.choices):
            raise ValueError(f"{self.field_id}: choices are given exactly for choice fields")
        if (self.type is FieldType.FILE) != (self.max_files is not None):
            raise ValueError(f"{self.field_id}: max_files is given exactly for file fields")
        return self


class FormTemplate(Contract):
    form_id: str = Field(pattern=r"^[a-z0-9_]+$")
    version: str = Field(pattern=r"^\d{4}-\d{4}(\.\d+)?$")
    title: str
    fields: list[FormField] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> Self:
        ids = [f.field_id for f in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate field ids")
        known = set(ids)
        for f in self.fields:
            if f.required_if and f.required_if.field_id not in known:
                raise ValueError(f"{f.field_id}: required_if refers to an unknown field")
        return self

    def field(self, field_id: str) -> FormField:
        for f in self.fields:
            if f.field_id == field_id:
                return f
        raise KeyError(field_id)


class AttachmentKind(StrEnum):
    POSTER = "poster"
    EXPENSE_FORM = "expense_form"
    FUNDING_CONFIRMATION = "funding_confirmation"
    SPEAKER_CV = "speaker_cv"
    GUEST_LIST = "guest_list"


class FieldAnswer(Contract):
    value: str | list[str] | None
    origin: Origin
    sources: list[SourceRef] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=300)


class AttachmentNeed(Contract):
    field_id: FormFieldId
    kind: AttachmentKind
    ready: bool
    file_ref: str | None = None


class DraftProposalRequest(Contract):
    spec: EventSpec
    rules: RuleApplication
    profile: ClubProfile
    requester: RequesterDetails
    template: FormTemplate

    @model_validator(mode="after")
    def _same_event(self) -> Self:
        if (self.rules.event_id, self.rules.spec_revision) != (self.spec.event_id, self.spec.revision):
            raise ValueError("rules were computed for a different event or an older spec revision")
        if self.profile.club_id != self.spec.club_id:
            raise ValueError("profile belongs to another club")
        return self


class ProposalDraft(Contract):
    form_id: str
    form_version: str
    event_id: EventId
    spec_revision: int = Field(ge=1)
    answers: dict[FormFieldId, FieldAnswer]
    attachments: list[AttachmentNeed] = Field(default_factory=list)
