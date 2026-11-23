"""F-301: Edit-then-approve on a "same as" (merge) card keeps the corrected wording; plain approve keeps the old."""

from __future__ import annotations

from datetime import date

from clubops.contracts.common import Role
from clubops.contracts.knowhow import ProposalOp, VerifyDecision, VerifyRequest
from tests.factories import NOW, actor, item, proposal, verified


def _merge_card(store):  # type: ignore[no-untyped-def]
    store.backend.append(
        verified(item("kh-gf-known", title="Green Field", statement="Book Green Field three weeks ahead."))
    )
    candidate = item("kh-gf-new", title="Green Field", statement="Book Green Field three weeks ahead.")
    card = proposal(candidate, ProposalOp.MERGE, pid="p-merge", target_item="kh-gf-known")
    store.submit(card)
    return card, candidate


def test_an_edit_on_a_merge_card_is_kept(store) -> None:  # type: ignore[no-untyped-def]
    card, candidate = _merge_card(store)
    edited = candidate.model_copy(update={"statement": "Book Green Field four weeks ahead."})
    request = VerifyRequest(proposal=card, decision=VerifyDecision.ACCEPT_EDITED, edited_candidate=edited)
    committed = store.verify(request, actor(Role.PRESIDENT), NOW).data.committed
    assert committed.item_id == "kh-gf-known" and committed.statement == "Book Green Field four weeks ahead."
    assert committed.version == 2  # the old wording stays in history


def test_a_plain_approve_on_a_merge_card_keeps_the_known_wording(store) -> None:  # type: ignore[no-untyped-def]
    card, _ = _merge_card(store)
    request = VerifyRequest(proposal=card, decision=VerifyDecision.ACCEPT)
    committed = store.verify(request, actor(Role.PRESIDENT), NOW).data.committed
    assert committed.statement == "Book Green Field three weeks ahead."


def test_an_end_date_typed_on_a_merge_card_is_kept(store) -> None:  # type: ignore[no-untyped-def]
    """Approving a "same as" card with a new end date used to keep the old one (F-306)."""
    card, candidate = _merge_card(store)
    edited = candidate.model_copy(update={"valid_to": date(2027, 5, 31)})
    request = VerifyRequest(proposal=card, decision=VerifyDecision.ACCEPT_EDITED, edited_candidate=edited)
    assert store.verify(request, actor(Role.PRESIDENT), NOW).data.committed.valid_to == date(2027, 5, 31)
