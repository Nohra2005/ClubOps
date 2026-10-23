"""Deterministic calendar items from an explicitly approved plan."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from clubops.contracts.calendar import CalendarItem, ItemKind, ItemStatus, Reminder
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
