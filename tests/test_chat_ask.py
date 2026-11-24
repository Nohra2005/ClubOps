"""Cited chat answers with synthetic facts and a fake model."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from clubops.capabilities.runner import Usage
from clubops.chat.ask import ask
from clubops.contracts.knowhow import Answer, AskRequest, ItemStatus, KnowHowItem
from clubops.model.budget import Budget
from tests.factories import TODAY, item, verified


class FakeStore:
    def __init__(self, facts: list[KnowHowItem]) -> None:
        self.facts = facts

    def search(self, club_id: str, text: str) -> list[KnowHowItem]:
        return [fact for fact in self.facts if fact.club_id == club_id]


class FakeModel:
    def __init__(self, answer: Answer) -> None:
        self.answer = answer
        self.called = False
        self.user = ""
        self.budget: Budget | None = None
        self.max_tokens = 0

    def complete(self, request: object, output: object, budget: Budget) -> tuple[Answer, Usage]:
        self.called = True
        self.user = request.user  # type: ignore[attr-defined]
        self.budget = budget
        self.max_tokens = request.max_tokens  # type: ignore[attr-defined]
        budget.check()
        budget.charge(Usage())
        return self.answer, Usage()


def question(club: str = "running-club", text: str = "Who books Green Field?") -> AskRequest:
    return AskRequest(club_id=club, question=text, as_of=TODAY)


def known(citations: list[str]) -> Answer:
    return Answer(known=True, text="Ask the events officer.", citations=citations, basis="verified")


def test_answer_uses_visible_verified_fact_and_redacts_question() -> None:
    fact = verified(item())
    model = FakeModel(known([fact.item_id]))
    answer = ask(question(text="Who books Green Field? Email me at sample@aub.edu.lb"), FakeStore([fact]), model)  # type: ignore[arg-type]
    assert answer.known
    assert answer.citations == [fact.item_id]
    assert "sample@aub.edu.lb" not in model.user
    assert "[EMAIL]" in json.loads(model.user)["question"]


def test_empty_or_other_club_facts_do_not_call_model() -> None:
    fact = verified(item())
    model = FakeModel(known([fact.item_id]))
    answer = ask(question(club="another-club"), FakeStore([fact]), model)  # type: ignore[arg-type]
    assert not answer.known
    assert answer.ask is not None
    assert not model.called


def test_model_cannot_cite_unseen_fact() -> None:
    fact = verified(item())
    answer = ask(question(), FakeStore([fact]), FakeModel(known(["kh-other-club-secret"])))  # type: ignore[arg-type]
    assert not answer.known
    assert answer.citations == []


def test_stale_fact_is_not_sent_to_model() -> None:
    fact = verified(item()).model_copy(update={"valid_to": date(2026, 10, 4)})
    model = FakeModel(known([fact.item_id]))
    answer = ask(question(), FakeStore([fact]), model)  # type: ignore[arg-type]
    assert not answer.known
    assert not model.called


def test_one_step_budget_is_passed_to_model() -> None:
    fact = verified(item())
    model = FakeModel(known([fact.item_id]))
    ask(question(), FakeStore([fact]), model)  # type: ignore[arg-type]
    assert model.budget is not None
    assert model.budget.max_steps == 1
    assert model.budget.max_usd == Decimal("0.05")
    assert model.budget.steps == 1


def test_model_uncertainty_is_preserved() -> None:
    fact = verified(item())
    uncertain = Answer(
        known=False,
        text="I don't know from these facts.",
        citations=[],
        basis="none",
        ask={"who": "Club president"},
        look_in="Club handover",
    )
    answer = ask(question(), FakeStore([fact]), FakeModel(uncertain))  # type: ignore[arg-type]
    assert not answer.known
    assert answer.ask == uncertain.ask


@pytest.mark.parametrize(
    "status", [ItemStatus.RETIRED, ItemStatus.SUPERSEDED, ItemStatus.DISPUTED, ItemStatus.PROPOSED]
)
def test_inactive_facts_never_reach_model(status: str) -> None:
    fact = verified(item()).model_copy(update={"status": status})
    model = FakeModel(known([fact.item_id]))
    assert not ask(question(), FakeStore([fact]), model).known  # type: ignore[arg-type]
    assert not model.called


def test_future_fact_never_reaches_model() -> None:
    fact = verified(item()).model_copy(update={"valid_from": date(2027, 1, 1)})
    model = FakeModel(known([fact.item_id]))
    assert not ask(question(), FakeStore([fact]), model).known  # type: ignore[arg-type]
    assert not model.called


def test_the_answer_limit_leaves_room_for_a_long_fact_list() -> None:
    """F-319: 600 tokens cut a real answer off mid-JSON and the cabinet member got an error."""
    fact = verified(item())
    model = FakeModel(known([fact.item_id]))
    ask(question(), FakeStore([fact]), model)  # type: ignore[arg-type]
    assert model.max_tokens >= 1500


def test_a_placeholder_is_filled_back_from_the_cited_fact_and_the_model_never_sees_the_number() -> None:
    """F-321: the answer said "[PHONE]" because personal data is hidden from the model; the asker needs the number."""
    fact = verified(item(statement="To book any room, cabinet members call +961 70 869 848."))
    model = FakeModel(
        Answer(known=True, text="Call [PHONE] to book a room.", citations=[fact.item_id], basis="verified")
    )
    answer = ask(question(text="Who do we call to book a room?"), FakeStore([fact]), model)  # type: ignore[arg-type]
    assert answer.text == "Call +961 70 869 848 to book a room."
    assert "869" not in model.user and "[PHONE]" in model.user


def test_a_placeholder_that_two_numbers_could_fill_is_left_alone() -> None:
    first = verified(item("kh-room-a", statement="Rooms: call +961 70 869 848."))
    second = verified(item("kh-room-b", statement="Gym: call +961 71 123 456."))
    model = FakeModel(Answer(known=True, text="Call [PHONE].", citations=["kh-room-a", "kh-room-b"], basis="verified"))
    answer = ask(question(), FakeStore([first, second]), model)  # type: ignore[arg-type]
    assert answer.text == "Call [PHONE]."
