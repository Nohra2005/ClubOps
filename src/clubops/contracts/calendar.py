"""Planner -> Google Calendar (docs/calendar-contract.md, D-45). ClubOps is the source of truth;
the calendar part (Joey) keeps Google in sync with these items."""

from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from clubops.contracts.common import ClubId, Contract, EventId, MemberId, Role
from clubops.contracts.planning import Plan

# "<event_id>/<task>" for an event's items, "club/<name>" for club-wide reminders.
CalendarItemId = Annotated[str, StringConstraints(pattern=r"^(ev-[a-z0-9-]{2,63}|club)/[a-z0-9][a-z0-9-]{1,63}$")]


class ItemKind(StrEnum):
    EVENT = "event"
    TASK = "task"


class ItemStatus(StrEnum):
    OPEN = "open"
    DONE = "done"  # keep the item, stop its reminders
    CANCELLED = "cancelled"  # delete it from the calendar


class Reminder(Contract):
    """Exactly one of the three."""

    before_days: int | None = Field(default=None, ge=0)
    on_day_at: time | None = None
    after_days: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _one(self) -> Self:
        if sum(v is not None for v in (self.before_days, self.on_day_at, self.after_days)) != 1:
            raise ValueError("a reminder is exactly one of before_days, on_day_at, after_days")
        return self


class CalendarItem(Contract):
    item_id: CalendarItemId = Field(description="stable: the same id updates the item, never duplicates it")
    club_id: ClubId
    event_id: EventId | None
    kind: ItemKind
    title: str = Field(min_length=3, max_length=200)
    date: date
    start: datetime | None = None
    end: datetime | None = None
    owner_role: Role | Literal["all_cabinet"]
    reminders: list[Reminder] = Field(default_factory=list)
    repeat_until_done: bool = False
    link: str | None = Field(default=None, max_length=300, description="opens the item in ClubOps")
    status: ItemStatus = ItemStatus.OPEN

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        club_wide = self.item_id.startswith("club/")
        if club_wide != (self.event_id is None):
            raise ValueError("club-wide items ('club/...') have no event; event items start with their event id")
        if self.event_id is not None and not self.item_id.startswith(self.event_id + "/"):
            raise ValueError("an event's item id starts with that event's id")
        if self.kind is ItemKind.EVENT:
            if self.start is None or self.end is None or self.end <= self.start:
                raise ValueError("an event item has a start and a later end")
            if self.start.tzinfo is None or self.end.tzinfo is None:
                raise ValueError("start and end are time-zone aware")
        elif self.start is not None or self.end is not None:
            raise ValueError("a task is all-day: no start or end")
        return self


class CalendarItemsRequest(Contract):
    club_id: ClubId
    event_id: EventId
    plan: Plan
    approved_by: MemberId = Field(description="items are only sent after a cabinet member approves the plan")


class CalendarItems(Contract):
    items: list[CalendarItem]
