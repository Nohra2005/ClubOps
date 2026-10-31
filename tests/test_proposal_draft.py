"""Synthetic proposal drafting through the frozen form contract."""

from __future__ import annotations

from datetime import datetime

from clubops.capabilities.validate import validate_answers
from clubops.contracts.club import CabinetSeat, ClubProfile, Person, RequesterDetails
from clubops.contracts.common import Role
from clubops.contracts.event import (
    Admission,
    AttendanceRange,
    Audience,
    EventSpec,
    EventType,
    Funding,
    Venue,
    VenueKind,
)
from clubops.contracts.forms import DraftProposalRequest, FormTemplate
from clubops.contracts.rules import RuleApplication
from clubops.drafts.proposal import draft_proposal


def request(template: FormTemplate, *, materials: bool = False) -> DraftProposalRequest:
    start = datetime.fromisoformat("2026-12-03T14:00:00+02:00")
    spec = EventSpec(
        event_id="ev-synthetic-workshop",
        club_id="math-club",
        revision=2,
        title="Spreadsheet workshop",
        event_type=EventType.WORKSHOP,
        description="A synthetic spreadsheet workshop for students.",
        start=start,
        end=datetime.fromisoformat("2026-12-03T16:00:00+02:00"),
        venue=Venue(kind=VenueKind.CLASSROOM, name="Synthetic classroom"),
        audience=Audience.AUB_ONLY,
        expected_attendance=AttendanceRange(low=25, high=30),
        admission=Admission.FREE,
        funding=[Funding.NO_EXPENSES],
        needs_materials=materials,
        has_catering=False,
        confirmed_by="m-president",
    )
    profile = ClubProfile(
        club_id="math-club",
        form_name="Synthetic Math Club",
        adviser=Person(first_name="Dr.", last_name="Example", aub_email="example@aub.edu.lb"),
        cabinet=[
            CabinetSeat(
                role=Role.PRESIDENT,
                member_id="m-president",
                person=Person(first_name="Alex", last_name="Sample", aub_email="alex@aub.edu.lb"),
                since=start.date(),
            )
        ],
        version=1,
    )
    return DraftProposalRequest(
        spec=spec,
        rules=RuleApplication(event_id=spec.event_id, spec_revision=2, rulebook=[], verdicts=[], requirements=[]),
        profile=profile,
        requester=RequesterDetails(member_id="m-president", aub_id="123456789", phone="12345678"),
        template=template,
    )


def test_fills_known_fields_and_leaves_unknowns_for_review(template: FormTemplate) -> None:
    draft = draft_proposal(request(template))
    assert draft.form_version == template.version
    assert draft.answers["q14"].value == "14:00"
    assert draft.answers["q16"].value == "16:00"
    assert draft.answers["q32"].value == "Example"
    assert draft.answers["q02"].value is None
    assert draft.answers["q27"].value == ["No expenses"]
    assert not validate_answers(template, draft)


def test_materials_use_a_supplied_extended_form_without_inventing_answers(template: FormTemplate) -> None:
    extra = {
        "field_id": "q34",
        "label": "How many tables?",
        "type": "text",
        "required": False,
        "required_if": {"field_id": "q19", "equals": "Yes"},
        "source": "human",
    }
    extended = FormTemplate.model_validate(
        {**template.model_dump(), "fields": [*template.model_dump()["fields"], extra]}
    )
    draft = draft_proposal(request(extended, materials=True))
    assert draft.answers["q19"].value == "Yes"
    assert draft.answers["q34"].value is None
    assert {issue.code for issue in validate_answers(extended, draft)} == {"form.required"}
