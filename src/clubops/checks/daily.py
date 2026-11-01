"""Find upcoming-event problems without contacting a model or sending messages."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from clubops.contracts.common import Role
from clubops.contracts.event import EventSpec, EventStatus
from clubops.contracts.planning import Plan


class FindingKind(StrEnum):
    OVERDUE = "overdue"
    DUE_SOON = "due_soon"
    OUTDATED_PLAN = "outdated_plan"


@dataclass(frozen=True)
class CheckEvent:
    spec: EventSpec
    plan: Plan | None
    status: EventStatus
    approved_revision: int | None
    done_tasks: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Finding:
    event_id: str
    kind: FindingKind
    owner_role: Role
    due: date
    task_id: str | None = None


def daily_findings(events: list[CheckEvent], today: date) -> list[Finding]:
    """Report each active club task problem once per run; the caller persists reminders."""
    found: list[Finding] = []
    for event in events:
        if event.status in {EventStatus.CANCELLED, EventStatus.CLOSED, EventStatus.DONE}:
            continue
        if event.spec.start is not None and event.spec.start.date() < today:
            continue
        plan = event.plan
        if plan is None:
            continue
        if plan.spec_revision != event.spec.revision or (
            event.status is EventStatus.APPROVED and event.approved_revision != event.spec.revision
        ):
            found.append(Finding(event.spec.event_id, FindingKind.OUTDATED_PLAN, Role.PRESIDENT, today))
            continue
        for task in plan.tasks:
            if task.task_id in event.done_tasks:
                continue
            days = (task.due - today).days
            if days < 0:
                kind = FindingKind.OVERDUE
            elif days <= 2:
                kind = FindingKind.DUE_SOON
            else:
                continue
            found.append(Finding(event.spec.event_id, kind, task.owner_role or Role.PRESIDENT, task.due, task.task_id))
    return found


def osa_page_digest(content: bytes) -> str:
    """Hash official OSA page bytes; a changed hash needs a human rule review."""
    return hashlib.sha256(content).hexdigest()


def osa_page_changed(content: bytes, previous_digest: str | None) -> bool:
    """A first successful fetch establishes a baseline, not a claim that rules changed."""
    return previous_digest is not None and osa_page_digest(content) != previous_digest
