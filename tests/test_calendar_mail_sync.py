"""Trusted mail -> durable per-role tasks -> fake Google; never contacts real accounts."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import httpx
import pytest

from clubops.calendar.queue import SyncQueue
from clubops.calendar.sync import CalendarSync, GoogleCalendarGateway, google_id
from clubops.contracts.calendar import (
    CalendarItem,
    DeadlineTask,
    DeadlineTasksRequest,
    HeldReason,
    ItemOrigin,
    ItemStatus,
)
from clubops.contracts.common import Role
from tests.test_calendar_sync import FakeGateway, task

TODAY = date(2026, 11, 23)
DIRECTORY = {
    Role.PRESIDENT: "president@example.com",
    Role.EVENTS: "events@example.com",
    Role.TREASURER: "treasurer@example.com",
    Role.ADVISER: "adviser@example.com",
    Role.MEMBER: "member@example.com",
}


def request(*, trusted: bool = True, day: date = date(2026, 12, 6), club: str = "math-club") -> DeadlineTasksRequest:
    return DeadlineTasksRequest(
        club_id=club,
        today=TODAY,
        trusted=trusted,
        tasks=[
            DeadlineTask(
                title="Send the synthetic report",
                date=day,
                owner_roles=[Role.EVENTS, Role.TREASURER],
                source_ref="kh-report",
            )
        ],
    )


def test_mail_creates_role_tasks_in_one_calendar_and_updates_without_duplicates(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "calendar.db")
    gateway = FakeGateway()
    sync = CalendarSync(gateway, {"math-club": "shared"})
    result = queue.enqueue_deadlines(request(), source_key="mail-1")
    assert len(result.items) == 2 and result.held == []
    queue.drain(sync, lambda _: DIRECTORY)
    assert len(gateway.events) == 6 and all(key.startswith("shared/") for key in gateway.events)
    for item in result.items:
        for suffix in ("", "reminder-0", "reminder-1"):
            body = gateway.events["shared/" + google_id(item.club_id, item.item_id, suffix)]
            assert body["attendees"] == [{"email": DIRECTORY[item.owner_role]}]
            assert body["guestsCanInviteOthers"] is False
            assert body["guestsCanModify"] is False
    queue.enqueue_deadlines(request(day=date(2026, 12, 10)), source_key="mail-2")
    queue.drain(sync, lambda _: DIRECTORY)
    assert len(gateway.events) == 6
    for item in queue.items("math-club"):
        primary = gateway.events["shared/" + google_id(item.club_id, item.item_id)]
        assert primary["start"] == {"date": "2026-12-10"}
        before = gateway.events["shared/" + google_id(item.club_id, item.item_id, "reminder-0")]
        assert before["start"] == {"dateTime": "2026-12-08T08:00:00", "timeZone": "Asia/Beirut"}


def test_untrusted_mail_cannot_queue_or_sync_and_unapproved_plans_stay_blocked(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "calendar.db")
    with pytest.raises(ValueError, match="passed every check"):
        queue.enqueue_deadlines(request(trusted=False), source_key="bad-mail")
    assert queue.pending() == [] and queue.held("math-club") == {}
    gateway = FakeGateway()
    sync = CalendarSync(gateway, {"math-club": "shared"})
    mail = queue.enqueue_deadlines(request(), source_key="good-mail").items[0]
    with pytest.raises(ValueError, match="approved"):
        sync.sync(mail, approved=False, role_emails=DIRECTORY)
    with pytest.raises(ValueError, match="approved"):
        sync.sync(task(), approved=False, trusted_mail=True, role_emails=DIRECTORY)
    assert gateway.events == {}
    sync.sync(mail, approved=False, trusted_mail=True, role_emails=DIRECTORY)
    assert len(gateway.events) == 3


def test_edits_and_removals_survive_sync_restart_and_stale_mail_snapshots(tmp_path: Path) -> None:
    path = tmp_path / "calendar.db"
    queue = SyncQueue(path)
    first, second = queue.enqueue_deadlines(request(), source_key="mail-1").items
    edited = first.model_copy(update={"title": "Our revised deadline", "date": date(2026, 12, 12)})
    queue.change(edited, approved=True)
    queue.remove(second.club_id, second.item_id, approved=True)
    gateway = FakeGateway()
    sync = CalendarSync(gateway, {"math-club": "shared"})
    queue.drain(sync, lambda _: DIRECTORY)
    restarted = SyncQueue(path)
    assert restarted.pending() == []
    result = restarted.enqueue_deadlines(request(day=date(2026, 12, 15)), source_key="mail-2")
    assert result.items == [] and [h.reason for h in result.held] == [HeldReason.EDITED, HeldReason.EDITED]
    assert restarted.pending() == []
    by_id = {item.item_id: item for item in restarted.items("math-club")}
    assert by_id[first.item_id].title == "Our revised deadline"
    assert by_id[first.item_id].origin is ItemOrigin.PERSON
    assert by_id[second.item_id].status is ItemStatus.CANCELLED
    assert restarted.held("math-club")["mail-2"] == result.held
    assert len(gateway.events) == 3


def test_holds_are_durable_scoped_and_replaced_on_mail_reprocessing(tmp_path: Path) -> None:
    path = tmp_path / "calendar.db"
    queue = SyncQueue(path)
    result = queue.enqueue_deadlines(request(day=date(2026, 1, 1)), source_key="mail-1")
    assert result.items == [] and result.held[0].reason is HeldReason.PAST
    restarted = SyncQueue(path)
    assert restarted.held("math-club")["mail-1"] == result.held
    assert restarted.held("other-club") == {} and restarted.items("other-club") == []
    assert restarted.pending() == []
    restarted.enqueue_deadlines(request(), source_key="mail-1")
    assert restarted.held("math-club") == {}
    assert len(restarted.pending()) == 2
    restarted.enqueue_deadlines(request(club="other-club"), source_key="mail-1")
    assert len(restarted.items("math-club")) == len(restarted.items("other-club")) == 2


def test_provider_failure_retries_after_restart_without_losing_mail_state(tmp_path: Path) -> None:
    path = tmp_path / "calendar.db"
    queue = SyncQueue(path)
    queue.enqueue_deadlines(request(), source_key="mail-1")
    gateway = FakeGateway()
    gateway.fail = True
    sync = CalendarSync(gateway, {"math-club": "shared"})
    assert queue.drain(sync, lambda _: DIRECTORY) == []
    restarted = SyncQueue(path)
    assert len(restarted.items("math-club")) == len(restarted.pending()) == 2
    gateway.fail = False
    assert len(restarted.drain(sync, lambda _: DIRECTORY)) == 2
    assert restarted.pending() == [] and len(gateway.events) == 6


def test_cabinet_change_replaces_attendees_and_done_removes_reminder_events() -> None:
    gateway = FakeGateway()
    sync = CalendarSync(gateway, {"math-club": "shared"})
    item = task()
    result = sync.sync(item, approved=True, role_emails={Role.PRESIDENT: DIRECTORY[Role.PRESIDENT]})
    assert result.missing_roles == (Role.EVENTS,)
    primary = "shared/" + google_id(item.club_id, item.item_id)
    assert gateway.events[primary]["attendees"] == [{"email": DIRECTORY[Role.PRESIDENT]}]
    sync.sync(item, approved=True, role_emails={Role.EVENTS: "new-holder@example.com"})
    assert len(gateway.events) == 3
    assert all(body["attendees"] == [{"email": "new-holder@example.com"}] for body in gateway.events.values())
    sync.sync(item.model_copy(update={"status": ItemStatus.DONE}), approved=True, role_emails={})
    assert len(gateway.events) == 1 and gateway.events[primary]["attendees"] == []
    sync.sync(item.model_copy(update={"status": ItemStatus.CANCELLED}), approved=True, role_emails={})
    assert gateway.events == {}


def test_all_cabinet_ignores_member_and_adviser_and_deduplicates_holders() -> None:
    gateway = FakeGateway()
    sync = CalendarSync(gateway, {"math-club": "shared"})
    item = task().model_copy(update={"owner_role": "all_cabinet"})
    sync.sync(item, approved=True, role_emails={**DIRECTORY, Role.SECRETARY: DIRECTORY[Role.PRESIDENT]})
    expected = [
        {"email": value} for value in sorted({DIRECTORY[r] for r in (Role.PRESIDENT, Role.EVENTS, Role.TREASURER)})
    ]
    assert all(body["attendees"] == expected for body in gateway.events.values())


@pytest.mark.parametrize("role", [Role.MEMBER, Role.ADVISER])
def test_non_cabinet_owner_is_rejected_before_any_write(role: Role) -> None:
    gateway = FakeGateway()
    sync = CalendarSync(gateway, {"math-club": "shared"})
    with pytest.raises(ValueError, match="cabinet"):
        sync.sync(task().model_copy(update={"owner_role": role}), approved=True, role_emails=DIRECTORY)
    assert gateway.events == {}


@pytest.mark.parametrize("directory", [{}, {Role.EVENTS: "not-an-address"}])
def test_missing_fallback_and_invalid_addresses_fail_before_writes(directory: dict[Role, str]) -> None:
    gateway = FakeGateway()
    with pytest.raises(ValueError, match=r"configured|configuration"):
        CalendarSync(gateway, {"math-club": "shared"}).sync(task(), approved=True, role_emails=directory)
    assert gateway.events == {}


def test_person_changes_require_approval_and_existing_club_item(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "calendar.db")
    with pytest.raises(ValueError, match="approval"):
        queue.change(task(), approved=False)
    with pytest.raises(ValueError, match="approval"):
        queue.remove("math-club", "ev-example/book-room", approved=False)
    with pytest.raises(ValueError, match="no calendar item"):
        queue.change(task(), approved=True)
    with pytest.raises(ValueError, match="no calendar item"):
        queue.remove("other-club", "ev-example/book-room", approved=True)
    with pytest.raises(ValueError, match="mail key"):
        queue.enqueue_deadlines(request(), source_key="")
    assert queue.pending() == []


def test_google_requests_notify_attendees_including_insert_race_and_cancellation() -> None:
    seen: list[httpx.Request] = []
    statuses = iter([404, 409, 200, 204])

    def handle(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(next(statuses), json={})

    gateway = GoogleCalendarGateway("synthetic-token", transport=httpx.MockTransport(handle))
    gateway.put("shared", "abc123", {"attendees": [{"email": DIRECTORY[Role.EVENTS]}]})
    gateway.delete("shared", "abc123")
    assert [req.method for req in seen] == ["PUT", "POST", "PUT", "DELETE"]
    assert all(req.url.params["sendUpdates"] == "all" for req in seen)


def test_existing_queue_is_migrated_without_losing_pending_items(tmp_path: Path) -> None:
    path = tmp_path / "old-calendar.db"
    item = task()
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(
            "CREATE TABLE pending_calendar (club_id TEXT NOT NULL, item_id TEXT NOT NULL, "
            "item_json TEXT NOT NULL, last_error TEXT, PRIMARY KEY (club_id, item_id))"
        )
        db.execute(
            "INSERT INTO pending_calendar VALUES (?, ?, ?, NULL)", (item.club_id, item.item_id, item.model_dump_json())
        )
    queue = SyncQueue(path)
    assert queue.items(item.club_id) == queue.pending() == [item]


def test_deadline_batch_rolls_back_state_pending_and_holds_on_storage_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue = SyncQueue(tmp_path / "calendar.db")
    original_save = SyncQueue._save
    calls = 0

    def failing_save(db: sqlite3.Connection, item: CalendarItem) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic storage failure")
        original_save(db, item)

    monkeypatch.setattr(SyncQueue, "_save", staticmethod(failing_save))
    with pytest.raises(OSError, match="storage failure"):
        queue.enqueue_deadlines(request(), source_key="mail-1")
    assert queue.items("math-club") == queue.pending() == []
    assert queue.held("math-club") == {}
