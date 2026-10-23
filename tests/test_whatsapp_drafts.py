from __future__ import annotations

import json

import pytest

from clubops.capabilities.runner import Usage
from clubops.contracts.drafts import Draft, DraftRequest, DraftType
from clubops.drafts.whatsapp import StyleExample, draft_event_messages, draft_whatsapp
from clubops.model import ModelRequest


class FakeModel:
    def __init__(self) -> None:
        self.prompt: ModelRequest | None = None

    def complete(self, request: ModelRequest, output: type[Draft], budget: object = None) -> tuple[Draft, Usage]:
        self.prompt = request
        payload = json.loads(request.user)
        return Draft(
            event_id=payload["event_id"],
            draft_type=payload["type"],
            template_version="whatsapp-style-1",
            body="See you there!",
        ), Usage()


def test_whatsapp_uses_only_approved_examples_from_this_club_and_redacts() -> None:
    model = FakeModel()
    draft = draft_whatsapp(
        DraftRequest(club_id="math-club", event_id="ev-example", draft_type=DraftType.WHATSAPP_ANNOUNCEMENT),
        event_facts={"title": "Puzzle night", "contact": "captain@example.com"},
        examples=[
            StyleExample("math-club", "Hey team! Email a@example.com", True),
            StyleExample("running-club", "Run with us!", True),
            StyleExample("math-club", "private draft", False),
        ],
        model=model,
    )
    assert draft.state == "draft"
    assert model.prompt is not None
    payload = json.loads(model.prompt.user)
    assert payload["style_examples"] == ["Hey team! Email [EMAIL]"]
    assert payload["verified_event_facts"]["contact"] == "[EMAIL]"
    assert "Run with us!" not in model.prompt.user
    assert "private draft" not in model.prompt.user


def test_whatsapp_requires_event_facts_and_matching_type() -> None:
    request = DraftRequest(club_id="math-club", event_id="ev-example", draft_type=DraftType.SPONSOR_EMAIL)
    with pytest.raises(ValueError, match="WhatsApp"):
        draft_whatsapp(request, event_facts={"title": "Puzzle night"}, examples=[], model=FakeModel())
    request = DraftRequest(club_id="math-club", event_id="ev-example", draft_type=DraftType.REMINDER_MESSAGE)
    with pytest.raises(ValueError, match="title"):
        draft_whatsapp(request, event_facts={}, examples=[], model=FakeModel())


def test_event_message_set_contains_announcement_and_reminder() -> None:
    drafts = draft_event_messages(
        "math-club",
        "ev-example",
        event_facts={"title": "Puzzle night"},
        examples=[],
        model=FakeModel(),
    )
    assert [draft.draft_type for draft in drafts] == [
        DraftType.WHATSAPP_ANNOUNCEMENT,
        DraftType.REMINDER_MESSAGE,
    ]
