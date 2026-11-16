"""Synthetic field-level proposal accuracy and CLI replay checks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.eval_proposals import score

from clubops.contracts.club import ClubProfile, Person, RequesterDetails
from clubops.contracts.event import EventSpec
from clubops.contracts.forms import DraftProposalRequest, FormTemplate
from clubops.contracts.rules import RuleApplication
from clubops.drafts.proposal import draft_proposal


def synthetic_case() -> tuple[DraftProposalRequest, dict[str, str | None]]:
    template = FormTemplate.model_validate(
        {
            "form_id": "synthetic_form",
            "version": "2026-2027",
            "title": "Synthetic form",
            "fields": [
                {"field_id": "q01", "label": "Club", "type": "text", "required": True, "source": "profile.form_name"},
                {"field_id": "q02", "label": "Event", "type": "text", "required": True, "source": "event.title"},
                {"field_id": "q03", "label": "Notes", "type": "text", "required": True, "source": "human"},
                {
                    "field_id": "q04",
                    "label": "Catering",
                    "type": "text",
                    "required": False,
                    "source": "event.has_catering",
                },
                {
                    "field_id": "q05",
                    "label": "Menu",
                    "type": "text",
                    "required": False,
                    "required_if": {"field_id": "q04", "equals": "Yes"},
                    "source": "human",
                },
            ],
        }
    )
    spec = EventSpec(
        event_id="ev-synthetic", club_id="synthetic-club", revision=1, title="Synthetic event", has_catering=True
    )
    request = DraftProposalRequest(
        spec=spec,
        rules=RuleApplication(event_id=spec.event_id, spec_revision=1, rulebook=[], verdicts=[], requirements=[]),
        profile=ClubProfile(
            club_id=spec.club_id,
            form_name="Synthetic Club",
            adviser=Person(first_name="Alex", last_name="Example", aub_email="alex@aub.edu.lb"),
            cabinet=[],
            version=1,
        ),
        requester=RequesterDetails(member_id="m-synthetic", aub_id="123456789", phone="12345678"),
        template=template,
    )
    return request, {"q01": "Synthetic Club", "q02": "Different title", "q03": "Human note", "q04": None, "q05": "Menu"}


def test_scoring_separates_correct_wrong_missing_and_invented() -> None:
    request, truth = synthetic_case()
    result = score("case-1", request, draft_proposal(request), truth)
    assert (result.correct, result.wrong, result.left_for_person, result.invented) == (1, 1, 1, 1)
    assert result.form_errors == 2
    with pytest.raises(ValueError, match="every non-file"):
        score("case-1", request, draft_proposal(request), {"q01": "Synthetic Club"})


def test_cli_replays_synthetic_case_without_outputting_answers(tmp_path: Path) -> None:
    request, truth = synthetic_case()
    cases = tmp_path / "cases.json"
    output = tmp_path / "score.md"
    cases.write_text(
        json.dumps([{"id": "case-1", "request": request.model_dump(mode="json"), "truth": truth}]),
        encoding="utf-8",
    )
    run = subprocess.run(  # noqa: S603 (fixed local test script and synthetic file paths)
        [sys.executable, "scripts/eval_proposals.py", "--cases", str(cases), "--out", str(output)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "| case-1 | 1 | 1 | 1 | 1 | 2 |" in run.stdout
    assert "Synthetic Club" not in run.stdout
    assert output.read_text(encoding="utf-8") == run.stdout
