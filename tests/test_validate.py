"""Form validators, including the failures found in a real draft (12-hour times)."""

from __future__ import annotations

from typing import Any

from clubops.capabilities.validate import submittable, validate_answers
from clubops.contracts.common import Origin
from clubops.contracts.forms import AttachmentKind, AttachmentNeed, FieldAnswer, FormTemplate, ProposalDraft

VALID: dict[str, Any] = {
    "q01": "Running Club",
    "q03": "Synthetic",
    "q04": "Tester",
    "q05": "202600000",
    "q06": "President",
    "q07": "st000@mail.aub.edu",
    "q08": "70000000",
    "q09": "Fall Campus Run",
    "q10": "Sport",
    "q13": "2026-11-07",
    "q14": "07:00",
    "q15": "2026-11-07",
    "q16": "09:00",
    "q17": "Green Field",
    "q18": "A 5 km run around campus.",
    "q19": "No",
    "q20": "No",
    "q22": "AUB students only",
    "q23": "50-70",
    "q25": "Free Entry",
    "q27": ["Club Account"],
    "q32": "Synthetic Adviser",
    "q33": "adviser@aub.edu.lb",
}


def draft(
    template: FormTemplate, overrides: dict[str, Any] | None = None, inferred: set[str] = frozenset(), attachments=()
) -> ProposalDraft:  # type: ignore[no-untyped-def, assignment]
    values = {**VALID, **(overrides or {})}
    answers = {
        k: FieldAnswer(value=v, origin=Origin.INFERRED if k in inferred else Origin.STATED)
        for k, v in values.items()
        if v is not None
    }
    return ProposalDraft(
        form_id=template.form_id,
        form_version=template.version,
        event_id="ev-fall-run",
        spec_revision=1,
        answers=answers,
        attachments=list(attachments),
    )


def codes(template: FormTemplate, **kw: Any) -> set[str]:
    return {i.code for i in validate_answers(template, draft(template, **kw))}


def test_valid_draft_is_submittable(template: FormTemplate) -> None:
    issues = validate_answers(template, draft(template))
    assert issues == []
    assert submittable(issues)


def test_twelve_hour_times_from_real_draft_are_rejected(template: FormTemplate) -> None:
    assert "form.time_24h_format" in codes(template, overrides={"q14": "3:30"})
    assert "form.time_24h_format" in codes(template, overrides={"q16": "5"})


def test_missing_required_field(template: FormTemplate) -> None:
    assert "form.required" in codes(template, overrides={"q33": None})


def test_other_event_type_requires_specification(template: FormTemplate) -> None:
    assert "form.required" in codes(template, overrides={"q10": "Other"})
    assert "form.required" not in codes(template, overrides={"q10": "Other", "q11": "Charity run"})


def test_non_aub_guests_require_guest_list_file(template: FormTemplate) -> None:
    assert "form.missing_attachment" in codes(template, overrides={"q22": "AUB students and Non-AUB students"})
    ready = [AttachmentNeed(field_id="q24", kind=AttachmentKind.GUEST_LIST, ready=True, file_ref="guests.xlsx")]
    found = codes(template, overrides={"q22": "AUB students and Non-AUB students"}, attachments=ready)
    assert "form.missing_attachment" not in found


def test_choice_must_be_an_option(template: FormTemplate) -> None:
    assert "form.bad_choice" in codes(template, overrides={"q10": "Marathon"})
    assert "form.bad_choice" in codes(template, overrides={"q27": ["Club Account", "Crowdfunding"]})


def test_end_before_start(template: FormTemplate) -> None:
    assert "form.end_before_start" in codes(template, overrides={"q16": "06:00"})


def test_non_aub_email_rejected(template: FormTemplate) -> None:
    assert "form.email_format" in codes(template, overrides={"q33": "adviser@gmail.com"})


def test_inferred_value_is_a_warning_not_an_error(template: FormTemplate) -> None:
    issues = validate_answers(template, draft(template, inferred={"q10"}))
    assert [i.code for i in issues] == ["form.inferred_needs_check"]
    assert submittable(issues)


def test_draft_for_another_form_version_is_rejected(template: FormTemplate) -> None:
    other = draft(template).model_copy(update={"form_version": "2025-2026"})
    assert [i.code for i in validate_answers(template, other)] == ["form.version_mismatch"]


def test_unknown_field_is_reported(template: FormTemplate) -> None:
    assert "form.unknown_field" in codes(template, overrides={"q99": "x"})
