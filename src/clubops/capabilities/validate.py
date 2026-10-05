"""Deterministic checks of a proposal draft against the form definition.

Every check exists because a real draft or interview showed the failure (see
docs/failure-matrix.md), e.g. 12-hour times on a 24-hour field.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date

from clubops.contracts.common import Issue, Origin, Severity
from clubops.contracts.forms import FieldType, FormTemplate, ProposalDraft

_PATTERNS: dict[FieldType, tuple[re.Pattern[str], str]] = {
    FieldType.TIME_24H: (re.compile(r"^([01]\d|2[0-3]):[0-5]\d$"), "use 24-hour HH:MM, e.g. 15:00"),
    FieldType.EMAIL: (re.compile(r"^[^@\s]+@(mail\.)?aub\.edu(\.lb)?$"), "use an AUB e-mail address"),
    FieldType.AUB_ID: (re.compile(r"^\d{9}$"), "an AUB ID has 9 digits"),
    FieldType.PHONE: (re.compile(r"^(\+961)?\d{7,8}$"), "a Lebanese number, 7-8 digits"),
    FieldType.COUNT_RANGE: (re.compile(r"^\d+(-\d+)?$"), "a number or a range such as 50-70"),
}


def _issue(
    code: str, field_id: str, message: str, fix: str | None = None, severity: Severity = Severity.ERROR
) -> Issue:
    return Issue(code=code, severity=severity, path=f"answers.{field_id}", message=message, fix=fix)


def validate_answers(template: FormTemplate, draft: ProposalDraft) -> list[Issue]:
    issues: list[Issue] = []
    if (draft.form_id, draft.form_version) != (template.form_id, template.version):
        return [
            Issue(
                code="form.version_mismatch", severity=Severity.ERROR, message="draft was made for another form version"
            )
        ]

    unknown = set(draft.answers) - {f.field_id for f in template.fields}
    issues += [_issue("form.unknown_field", fid, "field does not exist on this form") for fid in sorted(unknown)]

    def text(fid: str) -> str | None:
        ans = draft.answers.get(fid)
        return ans.value if ans and isinstance(ans.value, str) else None

    ready_files = {a.field_id for a in draft.attachments if a.ready}

    for field in template.fields:
        answer = draft.answers.get(field.field_id)
        value = answer.value if answer else None
        required = field.required or (
            field.required_if is not None and text(field.required_if.field_id) == field.required_if.equals
        )

        if field.type is FieldType.FILE:
            if required and field.field_id not in ready_files:
                issues.append(_issue("form.missing_attachment", field.field_id, f"'{field.label}' needs a file"))
            continue

        if answer is None or value in (None, "", []):
            if required:
                issues.append(_issue("form.required", field.field_id, f"'{field.label}' is required"))
            continue

        if answer.origin is Origin.INFERRED:
            issues.append(
                _issue(
                    "form.inferred_needs_check",
                    field.field_id,
                    "value was inferred by the model",
                    "confirm or correct it",
                    Severity.WARNING,
                )
            )

        if field.type is FieldType.SINGLE_CHOICE and value not in field.choices:
            issues.append(
                _issue("form.bad_choice", field.field_id, f"'{value}' is not an option", f"one of: {field.choices}")
            )
        elif field.type is FieldType.MULTI_CHOICE:
            values = value if isinstance(value, list) else [value]
            bad = [v for v in values if v not in field.choices]
            if bad:
                issues.append(_issue("form.bad_choice", field.field_id, f"not options: {bad}"))
        elif field.type is FieldType.DATE:
            try:
                date.fromisoformat(str(value))
            except ValueError:
                issues.append(_issue("form.date_format", field.field_id, f"'{value}' is not a date", "use YYYY-MM-DD"))
        elif field.type in _PATTERNS:
            pattern, fix = _PATTERNS[field.type]
            if not pattern.fullmatch(str(value)):
                issues.append(
                    _issue(f"form.{field.type.value}_format", field.field_id, f"'{value}' has the wrong format", fix)
                )

    issues += _check_time_order(text)
    return issues


def _check_time_order(text: Callable[[str], str | None]) -> list[Issue]:
    start_d, start_t, end_d, end_t = text("q13"), text("q14"), text("q15"), text("q16")
    if not all((start_d, start_t, end_d, end_t)):
        return []
    try:
        start = (date.fromisoformat(start_d or ""), start_t)
        end = (date.fromisoformat(end_d or ""), end_t)
    except ValueError:
        return []
    if end <= start:
        return [_issue("form.end_before_start", "q16", "the event ends before it starts")]
    return []


def submittable(issues: list[Issue]) -> bool:
    return not any(i.severity is Severity.ERROR for i in issues)
