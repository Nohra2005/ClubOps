"""Cited chat answers with synthetic facts and a fake model."""

from __future__ import annotations

import json

from clubops.capabilities.runner import Usage
from clubops.chat.ask import ask
from clubops.contracts.knowhow import Answer, AskRequest, KnowHowItem
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

    def complete(self, request: object, output: object, budget: object) -> tuple[Answer, Usage]:
        self.called = True
        self.user = request.user  # type: ignore[attr-defined]
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
