"""Synthetic checks for the six non-WhatsApp draft templates."""

from __future__ import annotations

import json

import pytest

from clubops.capabilities.runner import Usage
from clubops.contracts.drafts import Draft, DraftRequest, DraftType
from clubops.drafts.templates import draft_template
from clubops.drafts.whatsapp import StyleExample
from clubops.model import ModelRequest


class FakeModel:
    def __init__(self, *, wrong_event: bool = False, cited: bool = False) -> None:
        self.prompt: ModelRequest | None = None
        self.wrong_event = wrong_event
        self.cited = cited

    def complete(self, request: ModelRequest, output: type[Draft], budget: object = None) -> tuple[Draft, Usage]:
        self.prompt = request
        payload = json.loads(request.user)
        return Draft(
            event_id="ev-other" if self.wrong_event else payload["event_id"],
            draft_type=payload["draft_type"],
            template_version=request.prompt_version,
            subject="Sponsorship request" if payload["draft_type"] == DraftType.SPONSOR_EMAIL else None,
            body="Draft for cabinet review.",
            based_on=["kh-unsupplied"] if self.cited else [],
        ), Usage()


@pytest.mark.parametrize(
    "draft_type",
    [
        DraftType.SPONSOR_EMAIL,
        DraftType.INSTAGRAM_CAPTION,
        DraftType.POSTER_TEXT,
        DraftType.EXPENSE_FORM,
        DraftType.VOLUNTEER_SHIFTS,
        DraftType.IMPACT_REPORT,
    ],
)
def test_each_template_returns_an_unsent_club_specific_draft(draft_type: DraftType) -> None:
    model = FakeModel()
    draft = draft_template(
        DraftRequest(club_id="math-club", event_id="ev-puzzle", draft_type=draft_type),
        event_facts={"title": "Puzzle night", "contact": "alex@example.com"},
        examples=[
            StyleExample("math-club", "Friendly note from a@example.com", True),
            StyleExample("other-club", "Foreign style", True),
            StyleExample("math-club", "Unapproved private draft", False),
        ],
        model=model,
    )
    assert draft.state == "draft"
    assert draft.subject is not None if draft_type is DraftType.SPONSOR_EMAIL else draft.subject is None
    assert model.prompt is not None
    payload = json.loads(model.prompt.user)
    assert payload["verified_event_facts"]["contact"] == "[EMAIL]"
    assert payload["style_examples"] == ["Friendly note from [EMAIL]"]


def test_wrong_event_and_unsupplied_citation_are_rejected() -> None:
    request = DraftRequest(club_id="math-club", event_id="ev-puzzle", draft_type=DraftType.POSTER_TEXT)
    with pytest.raises(ValueError, match="different event"):
        draft_template(request, event_facts={"title": "Puzzle night"}, examples=[], model=FakeModel(wrong_event=True))
    with pytest.raises(ValueError, match="not supplied"):
        draft_template(request, event_facts={"title": "Puzzle night"}, examples=[], model=FakeModel(cited=True))


def test_missing_title_and_whatsapp_type_are_rejected() -> None:
    poster = DraftRequest(club_id="math-club", event_id="ev-puzzle", draft_type=DraftType.POSTER_TEXT)
    with pytest.raises(ValueError, match="title"):
        draft_template(poster, event_facts={}, examples=[], model=FakeModel())
    whatsapp = DraftRequest(club_id="math-club", event_id="ev-puzzle", draft_type=DraftType.WHATSAPP_ANNOUNCEMENT)
    with pytest.raises(ValueError, match="WhatsApp"):
        draft_template(whatsapp, event_facts={"title": "Puzzle night"}, examples=[], model=FakeModel())
