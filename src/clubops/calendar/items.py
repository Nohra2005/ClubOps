"""Deterministic calendar items from an explicitly approved plan."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from clubops.contracts.calendar import (
    CalendarItem,
    DeadlineItems,
    DeadlineTasksRequest,
    HeldDeadline,
    HeldReason,
    ItemKind,
    ItemOrigin,
    ItemStatus,
    Reminder,
)
from clubops.contracts.common import Role
from clubops.contracts.event import EventSpec
from clubops.contracts.planning import Plan


def event_items(spec: EventSpec, plan: Plan, *, approved: bool) -> list[CalendarItem]:
    if not approved:
        raise ValueError("only approved plans produce calendar items")
    if spec.event_id != plan.event_id or spec.revision != plan.spec_revision:
        raise ValueError("plan is stale or belongs to another event")
    if not spec.title or not spec.start or not spec.end:
        raise ValueError("event title, start and end are required")
    items = [
        CalendarItem(
            item_id=f"{spec.event_id}/event",
            club_id=spec.club_id,
            event_id=spec.event_id,
            kind=ItemKind.EVENT,
            title=spec.title,
            date=spec.start.date(),
            start=spec.start,
            end=spec.end,
            owner_role="all_cabinet",
            reminders=[Reminder(before_days=1)],
        )
    ]
    for task in plan.tasks:
        items.append(
            CalendarItem(
                item_id=f"{spec.event_id}/{task.task_id}",
                club_id=spec.club_id,
                event_id=spec.event_id,
                kind=ItemKind.TASK,
                title=task.title,
                date=task.due,
                owner_role=task.owner_role or Role.PRESIDENT,
                reminders=[Reminder(before_days=2), Reminder(on_day_at="08:00:00")],
            )
        )
    return items


def cancel_items(items: list[CalendarItem]) -> list[CalendarItem]:
    return [item.model_copy(update={"status": ItemStatus.CANCELLED}) for item in items]


def impact_form_item(club_id: str, event_id: str, event_end: datetime) -> CalendarItem:
    return CalendarItem(
        item_id=f"{event_id}/impact-form",
        club_id=club_id,
        event_id=event_id,
        kind=ItemKind.TASK,
        title="Fill the OSA impact report",
        date=event_end.date() + timedelta(days=2),
        owner_role=Role.PRESIDENT,
        reminders=[Reminder(on_day_at="08:00:00"), Reminder(after_days=3)],
        repeat_until_done=True,
    )


def osa_rule_checks(club_id: str, year: int, *, rules_received: bool) -> list[CalendarItem]:
    if rules_received:
        return []
    return [
        CalendarItem(
            item_id=f"club/osa-rule-check-{year}-{month:02d}",
            club_id=club_id,
            event_id=None,
            kind=ItemKind.TASK,
            title="Check the OSA rules page for this year's update",
            date=date(year, month, 1),
            owner_role=Role.PRESIDENT,
            reminders=[Reminder(on_day_at="09:00:00")],
        )
        for month in range(9, 13)
    ]


def cabinet_elections_item(club_id: str, year: int) -> CalendarItem:
    return CalendarItem(
        item_id=f"club/cabinet-elections-{year}",
        club_id=club_id,
        event_id=None,
        kind=ItemKind.TASK,
        title="Prepare cabinet elections",
        date=date(year, 4, 1),
        owner_role=Role.PRESIDENT,
        reminders=[Reminder(on_day_at="09:00:00")],
    )


MAX_DEADLINES_PER_MAIL = 10  # more than this in one e-mail looks like abuse: a person looks at it
MAX_DAYS_AHEAD = 366


def deadline_items(request: DeadlineTasksRequest) -> DeadlineItems:
    """Calendar tasks for the deadlines in a trusted OSA e-mail, added without a click (D-138).

    One task per role. The same fact always gets the same ids, so a later e-mail updates the task and never
    duplicates it. A task a person changed is never overwritten; odd dates and floods are held for a person."""
    if not request.trusted:
        raise ValueError("only mail that passed every check adds calendar tasks")
    changed = {i.item_id for i in request.existing if i.edited_by_person}
    items: list[CalendarItem] = []
    held: list[HeldDeadline] = []
    flood = len(request.tasks) > MAX_DEADLINES_PER_MAIL
    for task in request.tasks:
        reason = (
            HeldReason.TOO_MANY
            if flood
            else HeldReason.PAST
            if task.date < request.today
            else HeldReason.TOO_FAR
            if task.date > request.today + timedelta(days=MAX_DAYS_AHEAD)
            else None
        )
        if reason is not None:
            held.append(HeldDeadline(title=task.title, reason=reason))
            continue
        stamp = hashlib.sha256(task.source_ref.encode()).hexdigest()[:8]
        for role in task.owner_roles:
            item_id = f"club/dl-{stamp}-{role.value.replace('_', '-')}"
            if item_id in changed:
                held.append(HeldDeadline(title=task.title, reason=HeldReason.EDITED))
                continue
            items.append(
                CalendarItem(
                    item_id=item_id,
                    club_id=request.club_id,
                    event_id=None,
                    kind=ItemKind.TASK,
                    title=task.title,
                    date=task.date,
                    owner_role=role,
                    reminders=[Reminder(before_days=2), Reminder(on_day_at="08:00:00")],
                    origin=ItemOrigin.MAIL,
                    source_ref=task.source_ref,
                )
            )
    return DeadlineItems(items=items, held=held)
