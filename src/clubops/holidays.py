"""AUB holidays: offices are closed, so a deadline that falls on one is moved to the working
day before it. Event dates are not checked: the Student Activities office flags those.

Source: AUB HR "Holiday Calendar 2026-2027" (public page; dates marked * are tentative there).
Update once a year, like the OSA rules.
"""

from __future__ import annotations

from datetime import date, timedelta

from clubops.contracts.planning import Plan, PlanTask, TaskState

AUB_HOLIDAYS: dict[date, str] = {
    date(2026, 11, 22): "Independence Day",
    date(2026, 12, 24): "Christmas",
    date(2026, 12, 25): "Christmas",
    date(2027, 1, 1): "New Year's Day",
    date(2027, 1, 6): "Armenian Christmas",
    date(2027, 2, 9): "St. Maroun's Day",
    date(2027, 3, 9): "Eid al-Fitr (tentative)",
    date(2027, 3, 10): "Eid al-Fitr (tentative)",
    date(2027, 3, 25): "Annunciation Day",
    date(2027, 3, 26): "Good Friday (Latin)",
    date(2027, 3, 29): "Easter Monday (Latin)",
    date(2027, 4, 30): "Good Friday (Greek Orthodox)",
    date(2027, 5, 1): "Labor Day",
    date(2027, 5, 3): "Easter Monday (Greek Orthodox)",
}


def is_working_day(day: date, holidays: dict[date, str] = AUB_HOLIDAYS) -> bool:
    """AUB offices work Monday to Friday, except holidays."""
    return day.weekday() < 5 and day not in holidays


def working_days_before(day: date, n: int, holidays: dict[date, str] = AUB_HOLIDAYS) -> date:
    """The date n working days before ``day`` (OSA: '2 weeks before, excluding weekends and holidays')."""
    while n > 0:
        day -= timedelta(days=1)
        if is_working_day(day, holidays):
            n -= 1
    return day


def _state(due: date, today: date) -> TaskState:
    return TaskState.OVERDUE if due < today else TaskState.DUE_TODAY if due == today else TaskState.TODO


def move_off_holidays(plan: Plan, today: date, holidays: dict[date, str] = AUB_HOLIDAYS) -> tuple[Plan, list[str]]:
    """Move each deadline that lands on a holiday to the day before (repeatedly). Returns the notes."""
    notes: list[str] = []
    tasks: list[PlanTask] = []
    for original in plan.tasks:
        due = original.due
        while due in holidays:
            due -= timedelta(days=1)
        if due == original.due:
            tasks.append(original)
            continue
        notes.append(f"{original.task_id}: {original.due} is {holidays[original.due]}, so due {due}")
        tasks.append(original.model_copy(update={"due": due, "state": _state(due, today)}))
    tasks.sort(key=lambda t: (t.due, t.task_id))
    return plan.model_copy(update={"tasks": tasks}), notes
