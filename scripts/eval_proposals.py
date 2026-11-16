"""Score proposal drafts against private submitted answers without printing answer text.

Input JSON is a list of {id, request, truth}. `request` follows DraftProposalRequest;
`truth` maps form field IDs to submitted values, or null when the truth is unknown.
Keep real cases outside Git. This deterministic runner makes no model calls.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clubops.capabilities.validate import validate_answers
from clubops.contracts.common import Severity
from clubops.contracts.forms import DraftProposalRequest, FieldType, ProposalDraft
from clubops.drafts.proposal import draft_proposal


@dataclass(frozen=True)
class ProposalScore:
    case_id: str
    correct: int
    wrong: int
    left_for_person: int
    invented: int
    form_errors: int


def _same(actual: str | list[str], expected: str | list[str]) -> bool:
    if isinstance(actual, list) or isinstance(expected, list):
        return isinstance(actual, list) and isinstance(expected, list) and set(actual) == set(expected)
    return " ".join(actual.casefold().split()) == " ".join(expected.casefold().split())


def score(case_id: str, request: DraftProposalRequest, draft: ProposalDraft, truth: dict[str, Any]) -> ProposalScore:
    """Compare applicable non-file fields; null truth means no verified answer exists."""
    field_ids = {field.field_id for field in request.template.fields if field.type is not FieldType.FILE}
    if set(truth) != field_ids:
        raise ValueError("truth must name every non-file form field exactly once")
    if (draft.form_id, draft.form_version, draft.event_id, draft.spec_revision) != (
        request.template.form_id,
        request.template.version,
        request.spec.event_id,
        request.spec.revision,
    ):
        raise ValueError("draft does not match the case request")
    counts = {"correct": 0, "wrong": 0, "left_for_person": 0, "invented": 0}
    for field in request.template.fields:
        if field.type is FieldType.FILE:
            continue
        if field.required_if is not None and truth.get(field.required_if.field_id) != field.required_if.equals:
            continue
        expected = truth[field.field_id]
        actual = draft.answers.get(field.field_id)
        value = actual.value if actual is not None else None
        if expected is not None and not (
            isinstance(expected, str) or (isinstance(expected, list) and all(isinstance(x, str) for x in expected))
        ):
            raise ValueError(f"truth for {field.field_id} must be text, a text list, or null")
        if value in (None, "", []):
            if expected not in (None, "", []) or field.required:
                counts["left_for_person"] += 1
        elif expected in (None, "", []):
            counts["invented"] += 1
        elif _same(value, expected):
            counts["correct"] += 1
        else:
            counts["wrong"] += 1
    errors = sum(issue.severity is Severity.ERROR for issue in validate_answers(request.template, draft))
    return ProposalScore(case_id, **counts, form_errors=errors)


def table(scores: list[ProposalScore]) -> str:
    total = ProposalScore(
        "Total",
        *(
            sum(getattr(row, name) for row in scores)
            for name in ("correct", "wrong", "left_for_person", "invented", "form_errors")
        ),
    )
    lines = [
        "| Case | Correct | Wrong | Left for person | Invented | Form errors |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in [*scores, total]:
        lines.append(
            f"| {row.case_id} | {row.correct} | {row.wrong} | {row.left_for_person} | "
            f"{row.invented} | {row.form_errors} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path, help="private JSON cases")
    parser.add_argument("--out", type=Path, help="result table path; contains counts and case IDs only")
    args = parser.parse_args()
    raw = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("cases must be a JSON array")
    scores: list[ProposalScore] = []
    for case in raw:
        case_id = str(case["id"])
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", case_id):
            raise ValueError("case ID must contain only letters, digits, underscores or hyphens")
        request = DraftProposalRequest.model_validate(case["request"])
        truth = case["truth"]
        if not isinstance(truth, dict):
            raise ValueError("truth must be a field-to-answer object")
        draft = draft_proposal(request)
        scores.append(score(case_id, request, draft, truth))
    rendered = table(scores)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
