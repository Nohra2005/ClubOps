"""Fill the versioned OSA proposal from confirmed event, club and requester facts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from clubops.contracts.common import Origin, SourceKind, SourceRef
from clubops.contracts.event import EventSpec
from clubops.contracts.forms import (
    AttachmentKind,
    AttachmentNeed,
    DraftProposalRequest,
    FieldAnswer,
    FormField,
    ProposalDraft,
)


def _source(kind: SourceKind, source_id: str, locator: str) -> SourceRef:
    return SourceRef(kind=kind, source_id=source_id, locator=locator, observed_at=datetime.now(UTC))


def _event_value(spec: EventSpec, field: FormField) -> str | list[str] | None:
    name = field.source.removeprefix("event.")
    value: Any = getattr(spec, name.split(".")[0], None)
    if value is None or value == []:
        return None
    if name in {"start", "end"}:
        return str(value.date().isoformat() if field.type.value == "date" else value.strftime("%H:%M"))
    if name == "venue":
        return value.name or None
    if name == "expected_attendance":
        return str(value.low) if value.low == value.high else f"{value.low}-{value.high}"
    if name == "ticket_price":
        return f"{value.amount} {value.currency}"
    if name == "sdgs":
        return [next((choice for choice in field.choices if choice.startswith(f"SDG {n}:")), "") for n in value]
    if name == "catering_items":
        return ", ".join(value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return [
            _choice(item.value.replace("_", " ").replace("faculty department", "faculty/department"), field.choices)
            for item in value
        ]
    if hasattr(value, "value"):
        return _choice(value.value.replace("_", " "), field.choices)
    return str(value)


def _choice(value: str, choices: list[str]) -> str:
    return next((choice for choice in choices if choice.casefold() == value.casefold()), value)


def _profile_value(request: DraftProposalRequest, source: str) -> str | None:
    if source == "profile.form_name":
        return request.profile.form_name
    if source == "profile.adviser.name":
        adviser = request.profile.adviser
        name = f"{adviser.first_name} {adviser.last_name}".strip()
        return name if name.split()[0].rstrip(".").casefold() not in {"dr", "prof"} else " ".join(name.split()[1:])
    if source == "profile.adviser.aub_email":
        return str(request.profile.adviser.aub_email)
    return None


def _requester_value(request: DraftProposalRequest, source: str) -> str | None:
    seat = next((s for s in request.profile.cabinet if s.member_id == request.requester.member_id), None)
    if source == "requester.aub_id":
        return request.requester.aub_id.get_secret_value()
    if source == "requester.phone":
        return request.requester.phone.get_secret_value()
    if seat is None:
        return None
    if source == "requester.first_name":
        return seat.person.first_name
    if source == "requester.last_name":
        return seat.person.last_name
    if source == "requester.role":
        return seat.role.value.replace("_", " ").title()
    if source == "requester.aub_email":
        return str(seat.person.aub_email)
    return None


_ATTACHMENTS = {
    "attachment.speaker_cv": AttachmentKind.SPEAKER_CV,
    "attachment.guest_list": AttachmentKind.GUEST_LIST,
    "attachment.poster": AttachmentKind.POSTER,
    "attachment.expense_form": AttachmentKind.EXPENSE_FORM,
    "attachment.funding_confirmation": AttachmentKind.FUNDING_CONFIRMATION,
}


def draft_proposal(request: DraftProposalRequest) -> ProposalDraft:
    """Return a reviewable draft; unknown values and required files remain pending."""
    spec = request.spec
    answers: dict[str, FieldAnswer] = {}
    attachments: list[AttachmentNeed] = []
    for field in request.template.fields:
        if field.source.startswith("attachment."):
            kind = _ATTACHMENTS.get(field.source)
            if kind is not None:
                attachments.append(AttachmentNeed(field_id=field.field_id, kind=kind, ready=False))
            continue
        if field.source.startswith("event."):
            value = _event_value(spec, field)
            origin = Origin.STATED
            source = _source(SourceKind.USER_INPUT, spec.event_id, field.source)
        elif field.source.startswith("profile."):
            value = _profile_value(request, field.source)
            origin = Origin.RETRIEVED
            source = _source(SourceKind.USER_INPUT, request.profile.club_id, field.source)
        elif field.source.startswith("requester."):
            value = _requester_value(request, field.source)
            origin = Origin.STATED
            source = _source(SourceKind.USER_INPUT, request.requester.member_id, field.source)
        else:
            value = None
            origin = Origin.STATED
            source = None
        answers[field.field_id] = FieldAnswer(
            value=value,
            origin=origin,
            sources=[source] if source is not None and value is not None else [],
            note="Needs a person to fill or confirm" if value is None else None,
        )
    return ProposalDraft(
        form_id=request.template.form_id,
        form_version=request.template.version,
        event_id=spec.event_id,
        spec_revision=spec.revision,
        answers=answers,
        attachments=attachments,
    )
