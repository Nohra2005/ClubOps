"""Clean facts from trusted OSA mail apply without a click; odd ones wait; a person can edit or undo (D-138)."""

from __future__ import annotations

import pytest

from clubops.api import views
from clubops.capabilities.runner import CapabilityError
from clubops.contracts.common import ErrorCode, Role
from clubops.contracts.knowhow import ItemStatus, ProposalOp, Scope
from clubops.knowhow.store import AUTO_MEMBER
from tests.factories import CLUB, NOW, TODAY, actor, item, proposal, verified


def _known(store, **overrides):  # type: ignore[no-untyped-def]
    known = verified(item(**overrides))
    store.backend.append(known)
    return known


def test_a_clean_new_fact_is_added_without_a_click(store) -> None:  # type: ignore[no-untyped-def]
    store.submit(proposal())
    added = store.auto_apply("p-1", CLUB, NOW)
    assert added is not None and added.status is ItemStatus.VERIFIED and added.verified_by == AUTO_MEMBER
    assert store.pending == {} and [i.item_id for i in store.current(CLUB, TODAY)] == [added.item_id]


@pytest.mark.parametrize(
    "extra",
    [
        {"op": ProposalOp.CONTRADICTION, "target_item": "kh-other-fact", "conflicts_with": ["kh-other-fact"]},
        {"injection_flags": ["ignore previous instructions"]},
        {"rationale": "synthetic. This source may be outdated"},
        {"rationale": "synthetic. the sender is not on the OSA list: check it"},
    ],
)
def test_anything_odd_waits_for_a_person(store, extra) -> None:  # type: ignore[no-untyped-def]
    """F-257: a contradiction, hidden instructions, an outdated source or an unlisted sender are never auto-applied."""
    prop = proposal()
    store.submit(prop.model_copy(update=extra))
    assert store.auto_apply("p-1", CLUB, NOW) is None
    assert "p-1" in store.pending and store.current(CLUB, TODAY) == []


def test_a_newer_version_updates_the_old_one_and_undo_brings_it_back(store) -> None:  # type: ignore[no-untyped-def]
    old = _known(store)
    newer = item(statement="Book the green field four weeks ahead, not three.")
    store.submit(proposal(newer, ProposalOp.UPDATE, target_item=old.item_id))
    updated = store.auto_apply("p-1", CLUB, NOW)
    assert updated is not None and updated.version == 2 and updated.statement == newer.statement
    assert [v.version for v in store.history(old.item_id)] == [1, 2]
    undone = store.revise(old.item_id, actor(Role.EVENTS), NOW, undo=True)  # any cabinet member, club fact
    assert undone.version == 3 and undone.statement == old.statement and undone.status is ItemStatus.VERIFIED


def test_edit_applies_at_once_and_retire_can_be_undone(store) -> None:  # type: ignore[no-untyped-def]
    old = _known(store)
    edited = store.revise(old.item_id, actor(Role.TREASURER), NOW, statement="Book the green field a month ahead.")
    assert edited.version == 2 and edited.verified_by == "m-tester"
    retired = store.revise(old.item_id, actor(Role.TREASURER), NOW, retire=True)
    assert retired.status is ItemStatus.RETIRED
    assert store.revise(old.item_id, actor(Role.TREASURER), NOW, undo=True).status is ItemStatus.VERIFIED


def test_a_shared_fact_needs_a_president_unless_code_added_it(store) -> None:  # type: ignore[no-untyped-def]
    """F-258: a person-approved AUB fact stays president-only; one code added, any cabinet member can fix."""
    shared = _known(store, item_id="kh-shared-rule-a", scope=Scope.AUB, club_id=None)
    with pytest.raises(CapabilityError) as refused:
        store.revise(shared.item_id, actor(Role.EVENTS), NOW, statement="Changed by someone who is not a president.")
    assert refused.value.code is ErrorCode.NOT_AUTHORIZED
    auto = item(item_id="kh-shared-rule-b", scope=Scope.AUB, club_id=None)
    store.submit(proposal(auto, pid="p-2"))
    assert store.auto_apply("p-2", CLUB, NOW) is not None
    fixed = store.revise(auto.item_id, actor(Role.EVENTS), NOW, statement="Corrected by an events officer.")
    assert fixed.statement == "Corrected by an events officer."


def test_a_non_cabinet_member_cannot_change_a_fact(store) -> None:  # type: ignore[no-untyped-def]
    old = _known(store)
    with pytest.raises(CapabilityError) as refused:
        store.revise(old.item_id, actor(Role.MEMBER), NOW, statement="A member changes it.")
    assert refused.value.code is ErrorCode.NOT_AUTHORIZED


def test_add_as_new_rule_gets_its_own_id_when_the_card_carries_the_old_one(store) -> None:  # type: ignore[no-untyped-def]
    """F-260: an update card's candidate shares the known fact's id; keeping both needs a fresh id."""
    old = _known(store)
    store.submit(proposal(item(statement="A second, different statement."), ProposalOp.UPDATE, target_item=old.item_id))
    added = store.keep_both("p-1", None, None, actor(Role.PRESIDENT), NOW)
    assert added.item_id != old.item_id and store.latest(old.item_id).statement == old.statement  # type: ignore[union-attr]


def test_a_retirement_card_says_so(store) -> None:  # type: ignore[no-untyped-def]
    """F-250: the Review screen needs op=retire to tell the reviewer what Approve will do."""
    old = _known(store)
    card = views.review_card(proposal(item(), ProposalOp.RETIRE, target_item=old.item_id))
    assert card["op"] == "retire"
