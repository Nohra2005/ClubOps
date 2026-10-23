from __future__ import annotations

from datetime import date, datetime

import httpx
import pytest

from clubops.calendar.items import cabinet_elections_item, cancel_items, event_items, impact_form_item, osa_rule_checks
from clubops.calendar.sync import CalendarSync, GoogleCalendarGateway, SyncError, google_id
from clubops.contracts.calendar import CalendarItem, ItemKind, ItemStatus, Reminder
from clubops.contracts.common import Role
from clubops.contracts.event import EventSpec
from clubops.contracts.planning import Plan, PlanTask, TaskState


class FakeGateway:
    def __init__(self) -> None:
        self.events: dict[str, dict[str, object]] = {}
        self.fail = False

    def put(self, calendar_id: str, event_id: str, body: dict[str, object]) -> None:
        if self.fail:
            raise OSError("offline")
        self.events[f"{calendar_id}/{event_id}"] = body

    def delete(self, calendar_id: str, event_id: str) -> None:
        if self.fail:
            raise OSError("offline")
        self.events.pop(f"{calendar_id}/{event_id}", None)


def task() -> CalendarItem:
    return CalendarItem(
        item_id="ev-example/book-room",
        club_id="math-club",
        event_id="ev-example",
        kind=ItemKind.TASK,
        title="Book a room",
        date=date(2026, 11, 3),
        owner_role=Role.EVENTS,
        reminders=[Reminder(before_days=2), Reminder(on_day_at="08:00")],
    )


def test_approval_upsert_move_done_cancel_and_role_fallback() -> None:
    gateway = FakeGateway()
    sync = CalendarSync(
        gateway,
        {"math-club": "math-calendar@example.test"},
        {"math-club": {Role.PRESIDENT: "president-calendar", Role.EVENTS: "events-calendar"}},
    )
    item = task()
    with pytest.raises(ValueError, match="approved"):
        sync.sync(item, approved=False, role_emails={})
    assert gateway.events == {}
    result = sync.sync(item, approved=True, role_emails={Role.PRESIDENT: "president@example.test"})
    assert result.missing_roles == (Role.EVENTS,)
    assert len(gateway.events) == 3
    primary = "math-calendar@example.test/" + google_id(item.club_id, item.item_id)
    assert "president-calendar/" + google_id(item.club_id, item.item_id, "reminder-0") in gateway.events
    sync.sync(item, approved=True, role_emails={Role.EVENTS: "events@example.test"})
    assert len(gateway.events) == 3
    assert "events-calendar/" + google_id(item.club_id, item.item_id, "reminder-0") in gateway.events
    moved = item.model_copy(update={"date": date(2026, 11, 5)})
    sync.sync(moved, approved=True, role_emails={Role.EVENTS: "events@example.test"})
    assert gateway.events[primary]["start"] == {"date": "2026-11-05"}
    sync.sync(moved.model_copy(update={"status": ItemStatus.DONE}), approved=True, role_emails={})
    assert len(gateway.events) == 1
    sync.sync(moved.model_copy(update={"status": ItemStatus.CANCELLED}), approved=True, role_emails={})
    assert gateway.events == {}


def test_google_failure_is_retriable_and_club_ids_are_isolated() -> None:
    gateway = FakeGateway()
    gateway.fail = True
    sync = CalendarSync(gateway, {"math-club": "calendar"}, {"math-club": {Role.PRESIDENT: "president"}})
    with pytest.raises(SyncError, match="retry later"):
        sync.sync(task(), approved=True, role_emails={})
    assert google_id("math-club", "ev-example/book-room") != google_id("other-club", "ev-example/book-room")


def test_all_cabinet_reminders_use_private_role_calendars() -> None:
    gateway = FakeGateway()
    sync = CalendarSync(
        gateway,
        {"math-club": "shared"},
        {"math-club": {Role.PRESIDENT: "president-private", Role.EVENTS: "events-private"}},
    )
    item = task().model_copy(update={"owner_role": "all_cabinet"})
    sync.sync(item, approved=True, role_emails={})
    reminder_id = google_id(item.club_id, item.item_id, "reminder-0")
    assert "president-private/" + reminder_id in gateway.events
    assert "events-private/" + reminder_id in gateway.events
    assert "shared/" + reminder_id not in gateway.events


def test_google_http_put_then_insert_and_delete_missing() -> None:
    seen: list[tuple[str, str]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        if request.method == "PUT" and len(seen) == 1:
            return httpx.Response(404)
        if request.method == "DELETE":
            return httpx.Response(404)
        return httpx.Response(200 if request.method == "PUT" else 201, json={})

    gateway = GoogleCalendarGateway("synthetic-token", transport=httpx.MockTransport(handle))
    gateway.put("club@example.test", "abc123", {"summary": "Synthetic task"})
    gateway.delete("club@example.test", "abc123")
    assert [method for method, _ in seen] == ["PUT", "POST", "DELETE"]
    assert "club%40example.test" in seen[0][1]


def test_club_wide_and_after_event_reminders_are_multi_club() -> None:
    assert len(osa_rule_checks("math-club", 2026, rules_received=False)) == 4
    assert osa_rule_checks("math-club", 2026, rules_received=True) == []
    assert cabinet_elections_item("math-club", 2027).date == date(2027, 4, 1)
    impact = impact_form_item("math-club", "ev-example", datetime.fromisoformat("2026-11-03T12:00:00+02:00"))
    assert impact.date == date(2026, 11, 5)
    assert impact.reminders[0].on_day_at is not None
    assert impact.reminders[1].after_days == 3


def test_approved_plan_becomes_role_tasks_and_stale_plan_is_rejected() -> None:
    spec = EventSpec(
        event_id="ev-example",
        club_id="math-club",
        revision=2,
        title="Puzzle night",
        start=datetime.fromisoformat("2026-11-03T18:00:00+02:00"),
        end=datetime.fromisoformat("2026-11-03T20:00:00+02:00"),
    )
    plan = Plan(
        event_id="ev-example",
        spec_revision=2,
        feasible=True,
        tasks=[
            PlanTask(
                task_id="book-room",
                title="Book a room",
                due=date(2026, 10, 30),
                owner_role=Role.EVENTS,
                state=TaskState.TODO,
            )
        ],
    )
    with pytest.raises(ValueError, match="approved"):
        event_items(spec, plan, approved=False)
    items = event_items(spec, plan, approved=True)
    assert [(i.kind, i.owner_role) for i in items] == [(ItemKind.EVENT, "all_cabinet"), (ItemKind.TASK, Role.EVENTS)]
    assert all(i.status is ItemStatus.CANCELLED for i in cancel_items(items))
    with pytest.raises(ValueError, match="stale"):
        event_items(spec.model_copy(update={"revision": 3}), plan, approved=True)
