"""Contracts added in 0.2.0 (T-13): agent runs, calendar items, drafts, event status/history,
contacts and assets. Each test is one rule the other parts rely on. Synthetic data only."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from clubops.contracts.agent import AgentRun, AgentStep, RunStatus, StepState
from clubops.contracts.calendar import CalendarItem, ItemKind, Reminder
from clubops.contracts.directory import Asset, AssetKind, Contact
from clubops.contracts.drafts import Draft, DraftType
from clubops.contracts.event import EventRecord, EventStatus


def run(status: RunStatus, *states: StepState, **over: Any) -> AgentRun:
    steps = [AgentStep(n=i, tool="search-memory", text=f"step {i}", state=s) for i, s in enumerate(states, 1)]
    values: dict[str, Any] = {
        "run_id": "run-1",
        "club_id": "running-club",
        "event_id": "ev-test",
        "status": status,
        "steps": steps,
        "steps_used": len(steps),
        "step_limit": 8,
        "cost_usd": Decimal("0.01"),
        "cost_limit_usd": Decimal("0.05"),
    }
    values.update(over)
    return AgentRun(**values)


# ------------------------------------------------------------- agent run


def test_a_run_waits_for_the_user_exactly_when_its_last_step_is_a_question() -> None:
    run(RunStatus.WAITING_FOR_USER, StepState.DONE, StepState.QUESTION)
    with pytest.raises(ValidationError):
        run(RunStatus.WAITING_FOR_USER, StepState.DONE)
    with pytest.raises(ValidationError):
        run(RunStatus.RUNNING, StepState.QUESTION)


def test_a_run_never_reports_more_steps_than_its_limit() -> None:
    with pytest.raises(ValidationError):
        run(RunStatus.AT_LIMIT, StepState.DONE, steps_used=9)


def test_a_finished_run_names_its_event() -> None:
    run(RunStatus.DONE, StepState.DONE)
    with pytest.raises(ValidationError):
        run(RunStatus.DONE, StepState.DONE, event_id=None)


def test_steps_are_numbered_in_order() -> None:
    steps = [AgentStep(n=2, tool="apply-rules", text="x", state=StepState.DONE)]
    with pytest.raises(ValidationError):
        run(RunStatus.RUNNING, steps=steps, steps_used=1)


# --------------------------------------------------------------- calendar


def test_the_calendar_contract_examples_are_valid() -> None:
    """docs/calendar-contract.md and the code cannot drift apart."""
    text = Path("docs/calendar-contract.md").read_text()
    block = re.search(r"```json\n(.*?)```", text, re.DOTALL)
    assert block is not None
    for raw in json.loads(block.group(1)):
        CalendarItem.model_validate_json(json.dumps(raw))


def task(**over: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "item_id": "ev-test/book-room",
        "club_id": "running-club",
        "event_id": "ev-test",
        "kind": ItemKind.TASK,
        "title": "Book the room",
        "date": date(2026, 11, 1),
        "owner_role": "events",
    }
    values.update(over)
    return values


def test_item_ids_follow_their_event_or_are_club_wide() -> None:
    CalendarItem(**task())
    CalendarItem(**task(item_id="club/elections", event_id=None))
    for bad in (
        task(item_id="ev-other/book-room"),  # another event's prefix
        task(item_id="club/elections"),  # club-wide but tied to an event
        task(event_id=None),  # event prefix but no event
    ):
        with pytest.raises(ValidationError):
            CalendarItem(**bad)


def test_events_have_times_and_tasks_are_all_day() -> None:
    start = datetime(2026, 11, 1, 6, 0, tzinfo=UTC)
    CalendarItem(**task(item_id="ev-test/event", kind=ItemKind.EVENT, start=start, end=start.replace(hour=9)))
    with pytest.raises(ValidationError):
        CalendarItem(**task(kind=ItemKind.EVENT))  # no times
    with pytest.raises(ValidationError):
        CalendarItem(**task(kind=ItemKind.EVENT, start=start, end=start))  # ends when it starts
    with pytest.raises(ValidationError):
        CalendarItem(**task(start=start, end=start.replace(hour=9)))  # a task with times
    naive = datetime(2026, 11, 1, 6, 0)
    with pytest.raises(ValidationError):
        CalendarItem(**task(kind=ItemKind.EVENT, start=naive, end=naive.replace(hour=9)))


def test_a_reminder_is_exactly_one_kind() -> None:
    Reminder(before_days=2)
    Reminder(on_day_at=time(8, 0))
    with pytest.raises(ValidationError):
        Reminder()
    with pytest.raises(ValidationError):
        Reminder(before_days=2, after_days=2)


# ----------------------------------------------------------------- drafts


def test_emails_have_a_subject_and_other_drafts_do_not() -> None:
    Draft(event_id="ev-test", draft_type=DraftType.SPONSOR_EMAIL, template_version="t1", subject="Hi", body="x")
    Draft(event_id="ev-test", draft_type=DraftType.WHATSAPP_ANNOUNCEMENT, template_version="t1", body="x")
    with pytest.raises(ValidationError):
        Draft(event_id="ev-test", draft_type=DraftType.SPONSOR_EMAIL, template_version="t1", body="x")
    with pytest.raises(ValidationError):
        Draft(event_id="ev-test", draft_type=DraftType.POSTER_TEXT, template_version="t1", subject="x", body="x")


def test_a_draft_is_always_a_draft() -> None:
    with pytest.raises(ValidationError):
        Draft(event_id="ev-test", draft_type=DraftType.POSTER_TEXT, template_version="t1", body="x", state="sent")  # type: ignore[arg-type]


# ----------------------------------------------------- events and directory


def test_a_closed_event_records_its_outcome() -> None:
    base: dict[str, Any] = {"event_id": "ev-test", "club_id": "running-club", "title": "Run", "on": date(2026, 10, 7)}
    EventRecord(**base, status=EventStatus.DONE)
    EventRecord(**base, status=EventStatus.CLOSED, outcome="40 runners; 4-6 PM worked best")
    with pytest.raises(ValidationError):
        EventRecord(**base, status=EventStatus.CLOSED)


def test_contacts_can_be_shared_or_club_only() -> None:
    Contact(contact_id="ct-osa-office", club_id=None, name="Student Activities", organization="OSA")
    Contact(contact_id="ct-cafe", club_id="running-club", name="Cafe manager", organization="Cafe C")
    with pytest.raises(ValidationError):
        Contact(contact_id="bad-id", club_id=None, name="X", organization="Y")


def test_an_image_asset_gives_both_sizes_or_neither() -> None:
    common: dict[str, Any] = {
        "asset_id": "as-club-logo",
        "club_id": "running-club",
        "name": "Club logo",
        "kind": AssetKind.LOGO,
        "owner": "Running Club",
        "official": True,
        "file_ref": "assets/club-logo.png",
    }
    Asset(**common, width_px=1000, height_px=1000)
    Asset(**common, vector=True)
    with pytest.raises(ValidationError):
        Asset(**common, width_px=1000)


# ------------------------------------------------------------ club or society


def test_a_profile_is_a_club_unless_it_says_society() -> None:
    from clubops.contracts.club import ClubProfile, GroupKind, Person

    adviser = Person(first_name="Test", last_name="Adviser", aub_email="ta00@aub.edu.lb")
    base: dict[str, Any] = {"club_id": "asme", "form_name": "ASME", "adviser": adviser, "cabinet": [], "version": 1}
    assert ClubProfile(**base).kind is GroupKind.CLUB
    ClubProfile(**base, kind=GroupKind.SOCIETY, faculty="MSFEA")
    with pytest.raises(ValidationError):
        ClubProfile(**base, faculty="MSFEA")  # a club has no faculty
