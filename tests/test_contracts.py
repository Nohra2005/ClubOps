"""Contract invariants: invalid shapes are rejected at the boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from clubops.capabilities.registry import CAPABILITIES
from clubops.contracts.approvals import EmailPayload, ProposedAction, Risk, payload_sha256
from clubops.contracts.common import Contract, Error, ErrorCode, Result, Role, Status, TraceMeta
from clubops.contracts.event import EventSpec, EventType
from clubops.contracts.forms import FormTemplate
from clubops.contracts.handover import HandoverEntry
from clubops.contracts.knowhow import Answer, AskWho, ItemStatus, KnowHowProposal, ProposalOp, Scope
from tests.factories import CLUB, NOW, item, proposal, rule, source

TRACE = TraceMeta(trace_id="t" * 16, capability="ask", capability_version="0.1.0", started_at=NOW, latency_ms=1)


def test_result_ok_requires_data() -> None:
    with pytest.raises(ValidationError):
        Result[Answer](status=Status.OK, trace=TRACE)


def test_result_failed_requires_error_and_no_data() -> None:
    with pytest.raises(ValidationError):
        Result[Answer](status=Status.FAILED, trace=TRACE)
    ok = Result[Answer](status=Status.FAILED, error=Error(code=ErrorCode.INTERNAL, message="x"), trace=TRACE)
    assert ok.error is not None


def test_result_needs_input_requires_blocking_question() -> None:
    with pytest.raises(ValidationError):
        Result[Answer](status=Status.NEEDS_INPUT, trace=TRACE)


def test_club_item_needs_club_id_and_aub_item_forbids_it() -> None:
    with pytest.raises(ValidationError):
        item(club_id=None)
    with pytest.raises(ValidationError):
        item(scope=Scope.AUB)


def test_verified_item_names_verifier() -> None:
    with pytest.raises(ValidationError):
        item(status=ItemStatus.VERIFIED)


def test_rules_are_aub_scope_only() -> None:
    aub_rule = rule()
    with pytest.raises(ValidationError):
        item("kh-x", details=aub_rule.details)


def test_procedure_steps_numbered_in_order() -> None:
    bad = {"kind": "procedure", "goal": "g", "steps": [{"order": 2, "action": "a"}]}
    with pytest.raises(ValidationError):
        item(details=bad)


def test_proposal_must_quote_a_source() -> None:
    with pytest.raises(ValidationError):
        proposal(item(sources=[source(quote=None)]))


def test_update_proposal_needs_target_and_contradiction_names_conflicts() -> None:
    with pytest.raises(ValidationError):
        proposal(op=ProposalOp.UPDATE)
    with pytest.raises(ValidationError):
        proposal(op=ProposalOp.CONTRADICTION, target_item="kh-a")


def test_proposal_candidate_must_be_proposed_status() -> None:
    from tests.factories import verified

    with pytest.raises(ValidationError):
        KnowHowProposal(proposal_id="p-1", op=ProposalOp.CREATE, candidate=verified(item()), rationale="r")


def test_known_answer_cites_and_unknown_answer_does_not() -> None:
    with pytest.raises(ValidationError):
        Answer(known=True, text="yes", basis="verified")
    with pytest.raises(ValidationError):
        Answer(known=False, text="?", citations=["kh-a"], basis="none")
    with pytest.raises(ValidationError):
        Answer(known=False, text="Not in the club's know-how.", basis="none")  # must say who to ask
    Answer(known=False, text="Not in the club's know-how.", basis="none", ask=AskWho(who="the club president"))


def test_handover_entry_must_cite() -> None:
    with pytest.raises(ValidationError):
        HandoverEntry(text="Call the sponsor early")


def test_event_spec_invariants() -> None:
    start = datetime(2026, 11, 7, 7, 0, tzinfo=UTC)
    base = {"event_id": "ev-fall-run", "club_id": CLUB, "revision": 1}
    with pytest.raises(ValidationError):
        EventSpec(**base, start=start, end=start - timedelta(hours=1))
    with pytest.raises(ValidationError):
        EventSpec(**base, start=start.replace(tzinfo=None), end=start.replace(tzinfo=None) + timedelta(hours=1))
    with pytest.raises(ValidationError):
        EventSpec(**base, event_type=EventType.OTHER)
    with pytest.raises(ValidationError):
        EventSpec(**base, sdgs=[18])


def test_proposed_action_hash_must_match_payload() -> None:
    payload = EmailPayload(to=["sponsor@example.com"], subject="Water for our fall run", body="Hello")
    common = {
        "action_id": "a-1",
        "club_id": CLUB,
        "preview": "Email to sponsor",
        "risk": Risk.MEDIUM,
        "proposed_by": "suggest-replacement",
        "approver_roles": frozenset({Role.SPONSORSHIP}),
        "idempotency_key": "k-1",
        "created_at": NOW,
        "expires_at": NOW + timedelta(days=2),
    }
    ProposedAction(payload=payload, payload_sha256=payload_sha256(payload), **common)
    with pytest.raises(ValidationError):
        ProposedAction(payload=payload, payload_sha256="0" * 64, **common)


def test_contracts_are_strict() -> None:
    with pytest.raises(ValidationError):
        Answer(known=False, text="x", basis="none", ask=AskWho(who="the club president"), surprise="field")  # type: ignore[call-arg]


@pytest.mark.parametrize("spec", CAPABILITIES, ids=lambda s: s.name)
def test_registry_types_are_contracts(spec) -> None:  # type: ignore[no-untyped-def]
    for model in (spec.request, spec.response):
        assert issubclass(model, BaseModel)
        assert issubclass(model, Contract), f"{model.__name__} must extend Contract"


def test_registry_names_unique() -> None:
    names = [s.name for s in CAPABILITIES]
    assert len(names) == len(set(names))


def test_form_template_loads() -> None:
    raw = json.loads(Path("data/forms/osa_event_proposal_2026_2027.json").read_text())
    template = FormTemplate.model_validate(raw)
    assert len(template.fields) == 52  # every branch open, as on the live form
    assert len([f for f in template.fields if not f.required_if or f.field_id in {"q11", "q24", "q26", "q28"}]) == 33
    assert template.field("q38").required_if is not None and template.field("q38").required_if.field_id == "q37"
    assert template.field("q14").type.value == "time_24h"
    assert {f.field_id for f in template.fields if f.sensitive} == {"q05", "q08"}


def test_trace_meta_has_no_content_fields() -> None:
    assert not {"request", "response", "payload", "content", "text"} & set(TraceMeta.model_fields)
