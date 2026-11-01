"""Synthetic daily checks never call the model or send messages."""

from __future__ import annotations

from datetime import date, datetime

from clubops.checks.daily import CheckEvent, FindingKind, daily_findings, osa_page_changed, osa_page_digest
from clubops.contracts.common import Role
from clubops.contracts.event import EventSpec, EventStatus
from clubops.contracts.planning import Plan, PlanTask, TaskState


def event(
    *, revision: int = 1, status: EventStatus = EventStatus.APPROVED, done: frozenset[str] = frozenset()
) -> CheckEvent:
    spec = EventSpec(
        event_id="ev-synthetic-check",
        club_id="math-club",
        revision=revision,
        title="Synthetic puzzle night",
        start=datetime.fromisoformat("2026-11-10T18:00:00+02:00"),
        end=datetime.fromisoformat("2026-11-10T20:00:00+02:00"),
    )
    plan = Plan(
        event_id=spec.event_id,
        spec_revision=1,
        feasible=True,
        tasks=[
            PlanTask(
                task_id="late", title="Book room", due=date(2026, 10, 29), owner_role=Role.EVENTS, state=TaskState.TODO
            ),
            PlanTask(task_id="soon", title="Print cards", due=date(2026, 11, 1), state=TaskState.TODO),
            PlanTask(task_id="later", title="Send recap", due=date(2026, 11, 8), state=TaskState.TODO),
        ],
    )
    return CheckEvent(spec, plan, status, 1, done)


def test_overdue_due_soon_done_and_outdated_plan() -> None:
    today = date(2026, 10, 31)
    findings = daily_findings([event(done=frozenset({"soon"}))], today)
    assert [(f.kind, f.task_id, f.owner_role) for f in findings] == [(FindingKind.OVERDUE, "late", Role.EVENTS)]
    findings = daily_findings([event()], today)
    assert {(f.kind, f.task_id) for f in findings} == {
        (FindingKind.OVERDUE, "late"),
        (FindingKind.DUE_SOON, "soon"),
    }
    assert [f.kind for f in daily_findings([event(revision=2)], today)] == [FindingKind.OUTDATED_PLAN]
    assert daily_findings([event(status=EventStatus.CANCELLED)], today) == []


def test_osa_digest_detects_only_a_subsequent_change() -> None:
    first = b"synthetic official page version one"
    digest = osa_page_digest(first)
    assert not osa_page_changed(first, None)
    assert not osa_page_changed(first, digest)
    assert osa_page_changed(b"synthetic official page version two", digest)
