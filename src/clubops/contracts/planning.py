"""Backward plan from the event date. Fully deterministic."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import Field

from clubops.contracts.common import Contract, EventId, Role, Slug
from clubops.contracts.event import EventSpec
from clubops.contracts.rules import RuleApplication


class PlanRequest(Contract):
    spec: EventSpec
    rules: RuleApplication
    today: date


class TaskState(StrEnum):
    TODO = "todo"
    DUE_TODAY = "due_today"
    OVERDUE = "overdue"


class PlanTask(Contract):
    task_id: Slug
    title: str = Field(max_length=200)
    due: date
    owner_role: Role | None = None
    requirement_id: Slug | None = None
    state: TaskState


class Plan(Contract):
    event_id: EventId
    spec_revision: int = Field(ge=1)
    tasks: list[PlanTask]
    feasible: bool = Field(description="False when a lead time has already passed")
    earliest_feasible_date: date | None = None
