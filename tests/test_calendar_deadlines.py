"""Deadlines found in trusted OSA mail become calendar tasks without a click (D-138, F-253 to F-256)."""

from __future__ import annotations

from datetime import date

import pytest

from clubops.calendar.items import deadline_items
from clubops.contracts.calendar import (
    CalendarItem,
    DeadlineItems,
    DeadlineTask,
    DeadlineTasksRequest,
    HeldReason,
    ItemOrigin,
)
from clubops.contracts.common import Role

TODAY = date(2026, 11, 23)


def task(title: str = "Mid-year evaluation due", day: date = date(2026, 12, 6), roles=(Role.PRESIDENT,), ref="kh-eval"):  # type: ignore[no-untyped-def]
    return DeadlineTask(title=title, date=day, owner_roles=list(roles), source_ref=ref)


def request(
    *tasks: DeadlineTask, trusted: bool = True, existing: list[CalendarItem] | None = None
) -> DeadlineTasksRequest:
    return DeadlineTasksRequest(
        club_id="running-club", today=TODAY, trusted=trusted, tasks=list(tasks), existing=existing or []
    )


def test_each_role_gets_its_own_task_and_nobody_is_added_by_name() -> None:
    out = deadline_items(request(task(roles=(Role.TREASURER, Role.EVENTS))))
    assert {i.owner_role for i in out.items} == {Role.TREASURER, Role.EVENTS}
    assert len({i.item_id for i in out.items}) == 2 and out.held == []
    assert all(i.origin is ItemOrigin.MAIL and i.source_ref == "kh-eval" and i.event_id is None for i in out.items)


def test_the_same_fact_keeps_the_same_ids_so_a_later_mail_updates_and_never_duplicates() -> None:
    first = deadline_items(request(task())).items
    moved = deadline_items(request(task(day=date(2026, 12, 10)))).items
    assert [i.item_id for i in first] == [i.item_id for i in moved]
    assert moved[0].date == date(2026, 12, 10)


def test_mail_that_did_not_pass_every_check_adds_nothing() -> None:
    with pytest.raises(ValueError, match="passed every check"):
        deadline_items(request(task(), trusted=False))


def test_a_task_a_person_changed_is_not_overwritten() -> None:
    [auto] = deadline_items(request(task())).items
    edited = auto.model_copy(update={"title": "Mid-year evaluation (our version)", "edited_by_person": True})
    out = deadline_items(request(task(day=date(2026, 12, 20)), existing=[edited]))
    assert out.items == [] and [h.reason for h in out.held] == [HeldReason.EDITED]


def test_odd_dates_and_floods_are_held_for_a_person() -> None:
    out = deadline_items(request(task("Old", date(2026, 11, 1), ref="a"), task("Far away", date(2029, 1, 1), ref="b")))
    assert out.items == [] and [h.reason for h in out.held] == [HeldReason.PAST, HeldReason.TOO_FAR]
    many = [task(f"Deadline {n}", ref=f"kh-{n}") for n in range(11)]
    flood = deadline_items(request(*many))
    assert flood.items == [] and {h.reason for h in flood.held} == {HeldReason.TOO_MANY}


def test_a_deadline_goes_to_cabinet_roles_only() -> None:
    with pytest.raises(ValueError):
        task(roles=(Role.MEMBER,))
    with pytest.raises(ValueError):
        task(roles=(Role.PRESIDENT, Role.PRESIDENT))
    assert DeadlineItems(items=[], held=[]).held == []


def test_an_item_from_mail_must_name_its_fact() -> None:
    with pytest.raises(ValueError, match="names the fact"):
        CalendarItem(
            item_id="club/dl-abc12345-president",
            club_id="running-club",
            event_id=None,
            kind="task",
            title="Something due",
            date=TODAY,
            owner_role=Role.PRESIDENT,
            origin=ItemOrigin.MAIL,
        )  # type: ignore[arg-type]
