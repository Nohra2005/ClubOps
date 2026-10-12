"""Deterministic pieces of the event packet: requirement derivation and the backward plan."""

from __future__ import annotations

from datetime import date, timedelta

from clubops.capabilities.runner import CapabilityError, Outcome
from clubops.contracts.common import ErrorCode, ItemId, Question
from clubops.contracts.knowhow import KnowHowItem, RuleDetails
from clubops.contracts.planning import Plan, PlanRequest, PlanTask, TaskState
from clubops.contracts.rules import Applicability, DerivedRequirement, RuleVerdict


def derive_requirements(verdicts: list[RuleVerdict], rules: dict[ItemId, KnowHowItem]) -> list[DerivedRequirement]:
    """Union of the requirements of every rule judged APPLIES or UNCERTAIN.

    A requirement is ``uncertain`` only if no APPLIES verdict supports it.
    """
    merged: dict[str, tuple[DerivedRequirement, bool]] = {}
    for verdict in verdicts:
        if verdict.verdict is Applicability.NOT_APPLICABLE:
            continue
        item = rules.get(verdict.item_id)
        if item is None or item.version != verdict.item_version or not isinstance(item.details, RuleDetails):
            raise CapabilityError(
                ErrorCode.STALE_INPUT, f"verdict refers to an unknown rule version: {verdict.item_id}"
            )
        certain = verdict.verdict is Applicability.APPLIES
        for req in item.details.requirements:
            if req.requirement_id in merged:
                prev, prev_certain = merged[req.requirement_id]
                merged[req.requirement_id] = (
                    DerivedRequirement(
                        requirement=prev.requirement,
                        from_items=sorted({*prev.from_items, item.item_id}),
                        uncertain=not (prev_certain or certain),
                    ),
                    prev_certain or certain,
                )
            else:
                merged[req.requirement_id] = (
                    DerivedRequirement(requirement=req, from_items=[item.item_id], uncertain=not certain),
                    certain,
                )
    return [d for d, _ in sorted(merged.values(), key=lambda pair: pair[0].requirement.requirement_id)]


def plan_backward(request: PlanRequest) -> Outcome[Plan]:
    spec, rules, today = request.spec, request.rules, request.today
    if (rules.event_id, rules.spec_revision) != (spec.event_id, spec.revision):
        raise CapabilityError(ErrorCode.STALE_INPUT, "rules were computed for an older revision of the event")
    if spec.start is None:
        return Outcome(
            questions=[Question(question_id="event-start", text="When does the event start?", path="spec.start")]
        )

    event_day = spec.start.date()
    tasks: list[PlanTask] = []
    shortfall = 0
    for derived in rules.requirements:
        req = derived.requirement
        if req.lead_time_days is None:
            continue
        due = event_day - timedelta(days=req.lead_time_days)
        state = TaskState.OVERDUE if due < today else TaskState.DUE_TODAY if due == today else TaskState.TODO
        if state is TaskState.OVERDUE:
            shortfall = max(shortfall, (today - due).days)
        title = f"{req.name}{' (to confirm)' if derived.uncertain else ''}"
        tasks.append(
            PlanTask(task_id=req.requirement_id, title=title, due=due, requirement_id=req.requirement_id, state=state)
        )

    tasks.sort(key=lambda t: (t.due, t.task_id))
    feasible = shortfall == 0
    earliest: date | None = None if feasible else event_day + timedelta(days=shortfall)
    plan = Plan(
        event_id=spec.event_id,
        spec_revision=spec.revision,
        tasks=tasks,
        feasible=feasible,
        earliest_feasible_date=earliest,
    )
    return Outcome(data=plan)
