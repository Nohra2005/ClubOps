"""The event planner agent (T-14). A scripted model stands in for the real one, so every test
is free and gives the same result each time. Synthetic data only."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from clubops.agent.planner import EventFacts, ModelDecider, NextStep, Planner, RunState, Tool, build_prompt
from clubops.agent.rules_check import check_rules
from clubops.agent.runs import RunStore
from clubops.capabilities.runner import CapabilityError, Usage
from clubops.config import ModelMode, Settings
from clubops.contracts.agent import PlanEventRequest, RunStatus, StepState
from clubops.contracts.common import ErrorCode, SourceKind, SourceRef, Untrusted
from clubops.contracts.event import Audience, EventRecord, EventSpec, EventStatus, EventType, Venue, VenueKind
from clubops.contracts.knowhow import Requirement, RequirementKind, RuleDetails, Scope
from clubops.contracts.rules import Applicability
from clubops.knowhow.directory import Directory
from clubops.knowhow.store import KnowHowStore
from clubops.model.budget import Budget
from clubops.model.client import ModelClient
from tests.factories import CLUB, NOW, item, rule, verified

TODAY = date(2026, 10, 1)
START = datetime(2026, 10, 25, 6, 0, tzinfo=UTC)
STEP_COST = Decimal("0.001")


class Script:
    """Answers with the next scripted step; charges the budget like the real client does."""

    def __init__(self, *steps: NextStep | CapabilityError, repeat: NextStep | None = None) -> None:
        self.steps = list(steps)
        self.repeat = repeat
        self.prompts: list[str] = []

    def __call__(self, prompt: str, budget: Budget) -> NextStep:
        budget.check()
        budget.charge(Usage(cost_usd=STEP_COST))
        self.prompts.append(prompt)
        if self.steps:
            nxt = self.steps.pop(0)
        elif self.repeat is not None:
            nxt = self.repeat.model_copy(update={"query": f"{self.repeat.query} {len(self.prompts)}"})
        else:
            raise AssertionError("the script ran out of steps")
        if isinstance(nxt, CapabilityError):
            raise nxt
        return nxt


def step(tool: Tool, **kw: Any) -> NextStep:
    return NextStep(tool=tool, say=kw.pop("say", f"doing {tool}"), **kw)


FACTS = EventFacts(
    title="Campus fun run",
    event_type=EventType.SPORT,
    start=START,
    end=START.replace(hour=9),
    venue=Venue(kind=VenueKind.GREEN_FIELD, name="Green Field"),
    audience=Audience.AUB_AND_GUESTS,
    has_prizes=False,
    has_catering=False,
)


def full_plan() -> list[NextStep]:
    return [
        step(Tool.UPDATE_EVENT, facts=FACTS, say="Noting the date, place and who can come"),
        step(Tool.SEARCH_MEMORY, query="green field booking"),
        step(Tool.CHECK_RULES, say="Outside guests: checking the guest rule"),
        step(Tool.PLAN_TASKS),
        step(Tool.FINISH, say="Plan ready for approval"),
    ]


def request(text: str = "Fun run on Green Field on 25 Oct, open to friends from outside AUB") -> PlanEventRequest:
    words = Untrusted(content=text, source=SourceRef(kind=SourceKind.CHAT_MESSAGE, source_id="ui", observed_at=NOW))
    return PlanEventRequest(club_id=CLUB, description=words, today=TODAY)


@pytest.fixture
def directory(tmp_path: Path) -> Iterator[Directory]:
    d = Directory(tmp_path, CLUB)
    yield d
    d.close()


@pytest.fixture
def memory(store: KnowHowStore) -> KnowHowStore:
    store.backend.append(verified(rule()))
    return store


def planner(memory: KnowHowStore, directory: Directory, script: Script, **kw: Any) -> Planner:
    return Planner(script, memory, directory, **kw)


# ------------------------------------------------------------------ end to end


def test_it_plans_an_event_end_to_end_and_shows_its_steps(memory: KnowHowStore, directory: Directory) -> None:
    state = planner(memory, directory, Script(*full_plan())).start(request(), "run-a1")

    run = state.run
    assert run.status is RunStatus.DONE and run.event_id == "ev-a1"
    assert [s.tool for s in run.steps] == ["update-event", "search-memory", "check-rules", "plan-tasks", "finish"]
    assert all(s.state is StepState.DONE for s in run.steps)
    assert run.steps_used == 5 and run.cost_usd == 5 * STEP_COST
    assert state.plan is not None
    assert [t.task_id for t in state.plan.tasks] == ["guest-approval"]  # 14 days before 25 Oct
    assert state.plan.tasks[0].due == date(2026, 10, 11)
    saved = directory.event("ev-a1")
    assert saved is not None and saved.status is EventStatus.PLANNED  # waits for a person (D-41)


def test_it_asks_when_information_is_missing_and_continues_with_the_answer(
    memory: KnowHowStore, directory: Directory
) -> None:
    script = Script(step(Tool.ASK_USER, question="Which day is the run?"), *full_plan())
    agent = planner(memory, directory, script)

    waiting = agent.start(request("A fun run with outside friends"), "run-b2")
    assert waiting.run.status is RunStatus.WAITING_FOR_USER
    assert waiting.run.steps[-1].state is StepState.QUESTION
    assert waiting.run.steps[-1].text == "Which day is the run?"

    done = agent.answer(waiting, "Sunday 25 October, 6 to 9 AM")
    assert done.run.status is RunStatus.DONE
    assert done.run.steps[0].state is StepState.DONE  # the question is answered now
    assert "Sunday 25 October" in script.prompts[1]


def test_answering_a_run_that_is_not_waiting_is_refused(memory: KnowHowStore, directory: Directory) -> None:
    agent = planner(memory, directory, Script(*full_plan()))
    done = agent.start(request(), "run-c3")
    with pytest.raises(CapabilityError) as err:
        agent.answer(done, "hello")
    assert err.value.code is ErrorCode.CONFLICT


# ----------------------------------------------------------------------- limits


def test_it_stops_at_the_step_limit_and_can_be_continued(memory: KnowHowStore, directory: Directory) -> None:
    script = Script(repeat=step(Tool.SEARCH_MEMORY, query="anything"))
    agent = planner(memory, directory, script)

    stopped = agent.start(request(), "run-d4")
    assert stopped.run.status is RunStatus.AT_LIMIT
    assert stopped.run.steps_used == 8 and len(stopped.run.steps) == 8 and len(script.prompts) == 8

    more = agent.keep_going(stopped)
    assert more.run.status is RunStatus.AT_LIMIT
    assert more.run.steps_used == 16 and more.run.step_limit == 16


def test_it_stops_at_the_cost_limit(memory: KnowHowStore, directory: Directory) -> None:
    script = Script(repeat=step(Tool.SEARCH_MEMORY, query="anything"))
    agent = planner(memory, directory, script, cost_limit_usd=Decimal("0.003"))
    stopped = agent.start(request(), "run-e5")
    assert stopped.run.status is RunStatus.AT_LIMIT
    assert stopped.run.steps_used == 3 and stopped.run.cost_usd == Decimal("0.003")


def test_only_a_run_at_its_limit_can_be_continued(memory: KnowHowStore, directory: Directory) -> None:
    agent = planner(memory, directory, Script(*full_plan()))
    with pytest.raises(CapabilityError):
        agent.keep_going(agent.start(request(), "run-f6"))


# ---------------------------------------------------------------- guard rails


def test_it_cannot_finish_without_a_plan(memory: KnowHowStore, directory: Directory) -> None:
    script = Script(step(Tool.FINISH), *full_plan())
    state = planner(memory, directory, script).start(request(), "run-g7")
    first = state.run.steps[0]
    assert first.tool == "finish" and first.state is StepState.FAILED
    assert "no plan" in first.text
    assert state.run.status is RunStatus.DONE  # it recovered and finished properly


def test_a_plan_made_before_the_event_changed_is_not_enough(memory: KnowHowStore, directory: Directory) -> None:
    later = EventFacts(has_prizes=True)
    script = Script(
        *full_plan()[:4],
        step(Tool.UPDATE_EVENT, facts=later),
        step(Tool.FINISH),
        step(Tool.CHECK_RULES),
        step(Tool.PLAN_TASKS),
        step(Tool.FINISH),
    )
    state = planner(memory, directory, script, step_limit=10).start(request(), "run-h8")
    assert [s.state for s in state.run.steps][4:] == [
        StepState.DONE,
        StepState.FAILED,
        StepState.DONE,
        StepState.DONE,
        StepState.DONE,
    ]


def test_the_same_step_twice_in_a_row_is_refused(memory: KnowHowStore, directory: Directory) -> None:
    again = step(Tool.SEARCH_MEMORY, query="green field booking")
    script = Script(again, again, *full_plan()[:1], *full_plan()[2:])
    state = planner(memory, directory, script).start(request(), "run-i9")
    assert state.run.steps[1].state is StepState.FAILED
    assert state.run.status is RunStatus.DONE


def test_facts_that_do_not_fit_together_are_refused(memory: KnowHowStore, directory: Directory) -> None:
    backwards = EventFacts(start=START, end=START.replace(hour=5))
    script = Script(step(Tool.UPDATE_EVENT, facts=backwards), *full_plan())
    state = planner(memory, directory, script).start(request(), "run-j1")
    assert state.run.steps[0].state is StepState.FAILED
    assert state.run.status is RunStatus.DONE


def test_an_unreadable_model_answer_is_a_failed_step_not_a_crash(memory: KnowHowStore, directory: Directory) -> None:
    script = Script(CapabilityError(ErrorCode.MALFORMED_MODEL_OUTPUT, "bad json"), *full_plan())
    state = planner(memory, directory, script).start(request(), "run-k2")
    assert state.run.steps[0].state is StepState.FAILED
    assert state.run.status is RunStatus.DONE and state.run.steps_used == 6


def test_the_model_is_told_why_its_last_answer_was_rejected(memory: KnowHowStore, directory: Directory) -> None:
    bad = CapabilityError(ErrorCode.MALFORMED_MODEL_OUTPUT, "model answer did not match NextStep: facts.venue: bad")
    script = Script(bad, *full_plan())
    planner(memory, directory, script).start(request(), "run-k3")
    assert "your last answer was rejected (facts.venue: bad)" in script.prompts[1]


def test_when_the_model_cannot_be_reached_the_run_fails_cleanly(memory: KnowHowStore, directory: Directory) -> None:
    script = Script(CapabilityError(ErrorCode.UPSTREAM_TIMEOUT, "slow"))
    state = planner(memory, directory, script).start(request(), "run-l3")
    assert state.run.status is RunStatus.FAILED
    assert directory.event("ev-l3") is None  # nothing saved


def test_the_description_is_redacted_and_marked_as_data(memory: KnowHowStore, directory: Directory) -> None:
    script = Script(*full_plan())
    planner(memory, directory, script).start(request("Run on 25 Oct, call 76 123456 or a@b.com"), "run-m4")
    prompt = script.prompts[0]
    assert "76 123456" not in prompt and "a@b.com" not in prompt
    assert "<user_description>" in prompt


def test_search_memory_also_finds_similar_past_events(memory: KnowHowStore, directory: Directory) -> None:
    directory.put_event(
        EventRecord(
            event_id="ev-old-run",
            club_id=CLUB,
            title="Spring fun run",
            event_type=EventType.SPORT,
            on=date(2026, 4, 12),
            status=EventStatus.CLOSED,
            outcome="40 runners; 6 to 9 AM worked best",
        )
    )
    script = Script(full_plan()[0], step(Tool.SEARCH_MEMORY, query="fun run"), *full_plan()[2:])
    state = planner(memory, directory, script).start(request(), "run-n5")
    found = next(n for n in state.notes if n.startswith("memory 'fun run'"))
    assert "Spring fun run" in found and "6 to 9 AM worked best" in found


def test_a_deadline_on_a_holiday_moves_to_the_day_before(memory: KnowHowStore, directory: Directory) -> None:
    # guest approval is 14 days before the event; an 8 Jan event puts it on 25 Dec (Christmas)
    jan = START.replace(year=2027, month=1, day=8)
    facts = FACTS.model_copy(update={"start": jan, "end": jan.replace(hour=9)})
    script = Script(step(Tool.UPDATE_EVENT, facts=facts), *full_plan()[2:])
    state = planner(memory, directory, script).start(request(), "run-q8")
    assert state.plan is not None
    assert state.plan.tasks[0].due == date(2026, 12, 23)  # 25 and 24 Dec are both holidays
    assert any("is Christmas" in n for n in state.notes)


def test_a_run_survives_a_restart(tmp_path: Path, memory: KnowHowStore, directory: Directory) -> None:
    waiting = planner(memory, directory, Script(step(Tool.ASK_USER, question="When?"))).start(request(), "run-o6")
    runs = RunStore(tmp_path, CLUB)
    runs.save(waiting)
    runs.close()

    again = RunStore(tmp_path, CLUB)
    try:
        loaded = again.get("run-o6")
        assert loaded == waiting
        assert again.get("run-missing") is None
    finally:
        again.close()


# -------------------------------------------------------------------- rule check


def spec(**kw: Any) -> EventSpec:
    return EventSpec(event_id="ev-test", club_id=CLUB, revision=1, **kw)


def test_rules_apply_when_a_trigger_fits_and_are_uncertain_when_a_fact_is_missing() -> None:
    guests = verified(rule())
    assert check_rules(spec(audience=Audience.AUB_AND_GUESTS), [guests]).verdicts[0].verdict is Applicability.APPLIES
    assert check_rules(spec(audience=Audience.AUB_ONLY), [guests]).verdicts[0].verdict is Applicability.NOT_APPLICABLE
    unsure = check_rules(spec(), [guests])
    assert unsure.verdicts[0].verdict is Applicability.UNCERTAIN
    assert unsure.requirements[0].uncertain  # still listed, marked to confirm


def test_a_trigger_the_code_does_not_know_is_never_skipped() -> None:
    req = Requirement(requirement_id="adviser-ok", kind=RequirementKind.APPROVAL, name="Adviser approval")
    base = rule("kh-rule-odd")
    odd = verified(base.model_copy(update={"details": RuleDetails(triggers=["full_moon"], requirements=[req])}))
    result = check_rules(spec(audience=Audience.AUB_ONLY), [odd])
    assert result.verdicts[0].verdict is Applicability.UNCERTAIN
    assert "needs a person" in result.verdicts[0].reason


# ---------------------------------------------------------------- real client


def test_the_model_decider_uses_the_model_client(tmp_path: Path) -> None:
    answer = json.dumps({"tool": "check-rules", "say": "Checking the rules"})

    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": answer}}],
                "usage": {"prompt_tokens": 800, "completion_tokens": 40},
            },
        )

    settings = Settings(  # type: ignore[call-arg]
        base_url="https://provider.test/v1",
        api_key=SecretStr("sk-test"),
        model="fake-model",
        price_in_per_mtok=Decimal("1"),
        price_out_per_mtok=Decimal("2"),
        budget_usd_per_packet=Decimal("0.05"),
        max_steps_per_plan=8,
        mode=ModelMode.LIVE,
        recordings_dir=tmp_path / "rec",
        trace_path=tmp_path / "trace.jsonl",
    )
    budget = Budget(max_usd=Decimal("0.05"), max_steps=8)
    decided = ModelDecider(ModelClient(settings, transport=httpx.MockTransport(handle)))("prompt", budget)
    assert decided.tool is Tool.CHECK_RULES
    assert budget.steps == 1 and budget.spent_usd == Decimal("0.00088")


def test_the_prompt_stays_short(memory: KnowHowStore, directory: Directory) -> None:
    state = planner(memory, directory, Script(*full_plan())).start(request(), "run-p7")
    assert len(build_prompt(RunState.model_validate(state.model_dump()))) < 3000


def test_a_new_club_with_no_know_how_is_told_to_ask_not_guess(memory: KnowHowStore, directory: Directory) -> None:
    script = Script(full_plan()[0], step(Tool.SEARCH_MEMORY, query="sponsor contact"), *full_plan()[2:])
    state = planner(memory, directory, script).start(request(), "run-n6")
    found = next(n for n in state.notes if n.startswith("memory 'sponsor contact'"))
    assert "nothing approved found" in found and "never guess" in found


def test_an_aub_tip_from_a_club_is_not_shown_as_an_official_rule(memory: KnowHowStore, directory: Directory) -> None:
    tip = item("kh-west-hall", scope=Scope.AUB, club_id=None, title="West Hall rooms", tags=["west-hall"])
    memory.backend.append(verified(tip))
    script = Script(full_plan()[0], step(Tool.SEARCH_MEMORY, query="west hall"), *full_plan()[2:])
    state = planner(memory, directory, script).start(request(), "run-n7")
    found = next(n for n in state.notes if n.startswith("memory 'west hall'"))
    assert "West Hall rooms (AUB tip learned from a club, not an official rule)" in found
