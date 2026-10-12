"""Requirement derivation and the backward plan."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from clubops.capabilities.plan import derive_requirements, plan_backward
from clubops.capabilities.runner import CapabilityError
from clubops.contracts.event import EventSpec
from clubops.contracts.knowhow import Requirement, RequirementKind
from clubops.contracts.planning import PlanRequest, TaskState
from clubops.contracts.rules import Applicability, RuleApplication, RuleVerdict
from tests.factories import CLUB, rule

GUESTS = rule("kh-rule-guests")
EXPENSE = rule(
    "kh-rule-expense",
    Requirement(requirement_id="expense-form", kind=RequirementKind.FORM, name="Expense Form", lead_time_days=10),
    Requirement(
        requirement_id="guest-approval",
        kind=RequirementKind.APPROVAL,
        name="OSA approval for non-AUB guests",
        lead_time_days=14,
    ),
)
RULES = {r.item_id: r for r in (GUESTS, EXPENSE)}
SPEC = EventSpec(
    event_id="ev-fall-run",
    club_id=CLUB,
    revision=2,
    start=datetime(2026, 11, 7, 7, 0, tzinfo=UTC),
    end=datetime(2026, 11, 7, 9, 0, tzinfo=UTC),
)


def verdict(item_id: str, v: Applicability) -> RuleVerdict:
    return RuleVerdict(
        item_id=item_id,
        item_version=1,
        verdict=v,
        reason="synthetic",
        facts_used=[] if v is Applicability.UNCERTAIN else ["audience"],
    )


def application(*verdicts: RuleVerdict, revision: int = 2) -> RuleApplication:
    return RuleApplication(
        event_id="ev-fall-run",
        spec_revision=revision,
        rulebook=[(v.item_id, 1) for v in verdicts],
        verdicts=list(verdicts),
        requirements=derive_requirements(list(verdicts), RULES),
    )


def test_not_applicable_rules_add_nothing() -> None:
    assert derive_requirements([verdict("kh-rule-guests", Applicability.NOT_APPLICABLE)], RULES) == []


def test_shared_requirement_is_merged_and_certain_if_any_rule_applies() -> None:
    derived = derive_requirements(
        [verdict("kh-rule-guests", Applicability.UNCERTAIN), verdict("kh-rule-expense", Applicability.APPLIES)], RULES
    )
    by_id = {d.requirement.requirement_id: d for d in derived}
    assert by_id["guest-approval"].from_items == ["kh-rule-expense", "kh-rule-guests"]
    assert by_id["guest-approval"].uncertain is False


def test_uncertain_only_requirement_is_flagged() -> None:
    derived = derive_requirements([verdict("kh-rule-guests", Applicability.UNCERTAIN)], RULES)
    assert derived[0].uncertain is True


def test_verdict_on_unknown_rule_version_is_stale() -> None:
    bad = RuleVerdict(
        item_id="kh-rule-guests", item_version=9, verdict=Applicability.APPLIES, reason="x", facts_used=["audience"]
    )
    with pytest.raises(CapabilityError):
        derive_requirements([bad], RULES)


def test_due_dates_count_back_from_event_day() -> None:
    rules = application(verdict("kh-rule-expense", Applicability.APPLIES))
    plan = plan_backward(PlanRequest(spec=SPEC, rules=rules, today=date(2026, 10, 5))).data
    assert plan is not None and plan.feasible
    assert [(t.task_id, t.due) for t in plan.tasks] == [
        ("guest-approval", date(2026, 10, 24)),
        ("expense-form", date(2026, 10, 28)),
    ]


def test_passed_lead_time_makes_plan_infeasible_with_earliest_date() -> None:
    rules = application(verdict("kh-rule-expense", Applicability.APPLIES))
    plan = plan_backward(PlanRequest(spec=SPEC, rules=rules, today=date(2026, 10, 30))).data
    assert plan is not None and not plan.feasible
    assert plan.earliest_feasible_date == date(2026, 11, 13)
    assert {t.state for t in plan.tasks} == {TaskState.OVERDUE}


def test_uncertain_requirement_task_says_to_confirm() -> None:
    rules = application(verdict("kh-rule-guests", Applicability.UNCERTAIN))
    plan = plan_backward(PlanRequest(spec=SPEC, rules=rules, today=date(2026, 10, 5))).data
    assert plan is not None and plan.tasks[0].title.endswith("(to confirm)")


def test_rules_for_older_spec_revision_are_rejected() -> None:
    rules = application(verdict("kh-rule-guests", Applicability.APPLIES), revision=1)
    with pytest.raises(CapabilityError):
        plan_backward(PlanRequest(spec=SPEC, rules=rules, today=date(2026, 10, 5)))


def test_missing_start_asks_a_question() -> None:
    spec = EventSpec(event_id="ev-fall-run", club_id=CLUB, revision=2)
    outcome = plan_backward(PlanRequest(spec=spec, rules=application(), today=date(2026, 10, 5)))
    assert outcome.data is None and outcome.questions[0].question_id == "event-start"
