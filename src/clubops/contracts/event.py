"""Event intake: a cabinet member's description of an event, turned into a structured spec.

Enumerations mirror the OSA Event Proposal 2026-2027 form (data/forms/), so a spec maps
onto the form without translation. Unknown facts stay ``None`` and become questions.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from clubops.contracts.common import (
    ClubId,
    Contract,
    EventId,
    FieldPath,
    MemberId,
    Money,
    Origin,
    SourceRef,
    Untrusted,
)


class EventType(StrEnum):  # form Q10
    CONFERENCE = "conference"
    COMMUNITY_SERVICE = "community_service_event"
    CONCERT = "concert"
    DEBATE = "debate"
    EXHIBITION = "exhibition"
    FILM_SCREENING = "film_screening"
    GALA_DINNER = "gala_dinner"
    LECTURE = "lecture"
    MEETING = "meeting"
    PLAY = "play"
    RECEPTION = "reception"
    SPORT = "sport"
    TRIP = "trip"
    WORKSHOP = "workshop"
    OTHER = "other"


class Audience(StrEnum):  # form Q22
    AUB_ONLY = "aub_students_only"
    AUB_AND_GUESTS = "aub_and_non_aub_students"


class Admission(StrEnum):  # form Q25
    FREE = "free_entry"
    TICKET = "by_ticket"
    NOT_APPLICABLE = "not_applicable"


class Funding(StrEnum):  # form Q27
    CLUB_ACCOUNT = "club_account"
    EXTERNAL_SPONSOR = "external_sponsor"
    FACULTY_AID = "faculty_department_aid"
    USFC = "usfc"
    NO_EXPENSES = "no_expenses"


class VenueKind(StrEnum):
    GREEN_FIELD = "green_field"
    WEST_HALL = "west_hall"
    CLASSROOM = "classroom"
    OTHER_ON_CAMPUS = "other_on_campus"
    OFF_CAMPUS = "off_campus"
    ONLINE = "online"


class Venue(Contract):
    kind: VenueKind
    name: str = Field(max_length=120)


class AttendanceRange(Contract):
    low: int = Field(ge=1)
    high: int = Field(ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.high < self.low:
            raise ValueError("high < low")
        return self


class Speaker(Contract):
    first_name: str = Field(max_length=60)
    last_name: str = Field(max_length=60)
    nationality: str = Field(max_length=60)
    topic: str = Field(max_length=200)


class EventSpec(Contract):
    event_id: EventId
    club_id: ClubId
    revision: int = Field(ge=1, description="bumped on every change; downstream outputs record the revision they used")
    title: str | None = Field(default=None, max_length=150)
    event_type: EventType | None = None
    event_type_other: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    start: datetime | None = None
    end: datetime | None = None
    venue: Venue | None = None
    audience: Audience | None = None
    expected_attendance: AttendanceRange | None = None
    admission: Admission | None = None
    ticket_price: Money | None = None
    funding: list[Funding] = Field(default_factory=list)
    needs_materials: bool | None = None
    has_catering: bool | None = None
    catering_items: list[str] = Field(default_factory=list)
    has_prizes: bool | None = None
    has_sales: bool | None = None
    speakers: list[Speaker] = Field(default_factory=list)
    sdgs: list[int] = Field(default_factory=list)
    estimated_budget: Money | None = None
    collaborating_clubs: list[ClubId] = Field(default_factory=list)
    confirmed_by: MemberId | None = Field(default=None, description="set when a cabinet member confirms the spec")

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        if self.start and self.end:
            if self.start.tzinfo is None or self.end.tzinfo is None:
                raise ValueError("start and end must be timezone-aware")
            if self.end <= self.start:
                raise ValueError("end must be after start")
        if (self.event_type is EventType.OTHER) != (self.event_type_other is not None):
            raise ValueError("event_type_other is given exactly when event_type is 'other'")
        if self.ticket_price is not None and self.admission is not Admission.TICKET:
            raise ValueError("ticket_price only applies to ticketed events")
        if any(not 1 <= g <= 17 for g in self.sdgs) or len(set(self.sdgs)) != len(self.sdgs):
            raise ValueError("sdgs are distinct integers 1..17")
        if Funding.NO_EXPENSES in self.funding and len(self.funding) > 1:
            raise ValueError("'no_expenses' excludes other funding sources")
        return self

    @property
    def confirmed(self) -> bool:
        return self.confirmed_by is not None


class FieldProvenance(Contract):
    origin: Origin
    sources: list[SourceRef] = Field(default_factory=list)


class IntakeRequest(Contract):
    club_id: ClubId
    description: Untrusted = Field(description="the cabinet member's own words; treated as data, not instructions")
    now: datetime
    existing: EventSpec | None = Field(default=None, description="set when revising a spec")


class EventDraft(Contract):
    """Output of intake. Every non-empty field has a provenance entry."""

    spec: EventSpec
    provenance: dict[FieldPath, FieldProvenance]

    @model_validator(mode="after")
    def _provenance_complete(self) -> Self:
        filled = {
            name
            for name, value in self.spec
            if name not in {"event_id", "club_id", "revision", "confirmed_by"} and value not in (None, [], "")
        }
        missing = filled - set(self.provenance)
        if missing:
            raise ValueError(f"fields without provenance: {sorted(missing)}")
        return self


# ------------------------------------------------------------ status and history


class EventStatus(StrEnum):
    """Where an event is in its life (UI spec, Events screen)."""

    DRAFT = "draft"  # details being filled
    PLANNED = "planned"  # the agent made a plan; waiting for a cabinet member to approve it
    APPROVED = "approved"  # plan approved; calendar items sent
    DONE = "done"  # the date has passed; after-event form due
    CLOSED = "closed"  # after-event form filled
    CANCELLED = "cancelled"


class EventRecord(Contract):
    """A past or current event, kept as history (D-21). Know-how support points here."""

    event_id: EventId
    club_id: ClubId
    title: str = Field(max_length=150)
    event_type: EventType | None = None
    on: date
    status: EventStatus
    spec_revision: int | None = Field(default=None, ge=1)
    participants: int | None = Field(default=None, ge=0)
    sponsors: list[str] = Field(default_factory=list)
    partners: list[str] = Field(default_factory=list, description="other clubs or organizations")
    outcome: str | None = Field(default=None, max_length=1000, description="from the after-event form")

    @model_validator(mode="after")
    def _closed(self) -> Self:
        if self.status is EventStatus.CLOSED and self.outcome is None:
            raise ValueError("a closed event records its outcome (the after-event form)")
        return self
