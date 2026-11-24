"""Clean facts from trusted OSA mail apply without a click; odd ones wait; a person can edit or undo (D-138)."""

from __future__ import annotations

from datetime import date

import pytest

from clubops.api import views
from clubops.capabilities.runner import CapabilityError
from clubops.contracts.common import ErrorCode, Role
from clubops.contracts.knowhow import ItemStatus, ProposalOp, Scope
from clubops.knowhow.store import AUTO_MEMBER, KnowHowStore
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


def test_an_automatic_update_does_not_open_a_person_approved_shared_fact(store) -> None:  # type: ignore[no-untyped-def]
    """F-265 (1): the origin decides, not the latest stamp. A president-approved AUB fact that mail later updates
    stays president-only: an events officer still cannot edit, retire or undo it."""
    human = _known(store, item_id="kh-shared-rule-c", scope=Scope.AUB, club_id=None)
    newer = item(
        item_id="kh-shared-rule-c", scope=Scope.AUB, club_id=None, statement="Fill the impact report by 6 Dec."
    )
    store.submit(proposal(newer, ProposalOp.UPDATE, target_item=human.item_id, pid="p-3"))
    updated = store.auto_apply("p-3", CLUB, NOW)
    assert updated is not None and updated.verified_by == AUTO_MEMBER
    officer = actor(Role.EVENTS)
    for change in ({"statement": "Edited by an officer."}, {"retire": True}, {"undo": True}):
        with pytest.raises(CapabilityError) as refused:
            store.revise(human.item_id, officer, NOW, **change)
        assert refused.value.code is ErrorCode.NOT_AUTHORIZED
    assert not store.added_by_code(human.item_id)


def test_an_officers_correction_of_an_automatic_fact_can_still_be_undone(store) -> None:  # type: ignore[no-untyped-def]
    """F-265 (2): edit, retire and undo stay open to any cabinet member on a fact code first added, however many
    times a person has stamped it."""
    auto = item(item_id="kh-shared-rule-d", scope=Scope.AUB, club_id=None)
    store.submit(proposal(auto, pid="p-4"))
    assert store.auto_apply("p-4", CLUB, NOW) is not None
    officer = actor(Role.EVENTS)
    edited = store.revise(auto.item_id, officer, NOW, statement="Corrected by an events officer.")
    assert edited.verified_by == officer.member_id and store.added_by_code(auto.item_id)
    undone = store.revise(auto.item_id, officer, NOW, undo=True)
    assert undone.statement == auto.statement
    retired = store.revise(auto.item_id, officer, NOW, retire=True)
    assert retired.status is ItemStatus.RETIRED
    assert store.revise(auto.item_id, officer, NOW, undo=True).status is ItemStatus.VERIFIED


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


def test_a_retired_fact_told_again_comes_back_and_undo_retires_it_again(store) -> None:  # type: ignore[no-untyped-def]
    """F-302: re-learning a retired fact gave the same id and failed with "an item with this id already exists",
    so the card could never be approved (auto-apply left it in Review for good). It now returns as the next version."""
    fact = item("kh-guest-parking", title="Guest parking", statement="Guests park behind West Hall with a permit.")
    store.backend.append(verified(fact))
    president = actor(Role.PRESIDENT)
    store.revise(fact.item_id, president, NOW, retire=True)
    assert store.current(CLUB, TODAY) == []
    store.submit(proposal(fact.model_copy(update={"status": ItemStatus.PROPOSED, "version": 1}), pid="p-again"))
    back = store.auto_apply("p-again", CLUB, NOW)
    assert back is not None and back.status is ItemStatus.VERIFIED and back.version == 3
    assert [i.item_id for i in store.current(CLUB, TODAY)] == [fact.item_id] and store.pending == {}
    undone = store.revise(fact.item_id, president, NOW, undo=True)
    assert undone.status is ItemStatus.RETIRED and store.current(CLUB, TODAY) == []  # Undo goes back to retired


def test_a_verified_fact_is_still_not_created_twice(store) -> None:  # type: ignore[no-untyped-def]
    known = _known(store)
    store.submit(proposal(known.model_copy(update={"status": ItemStatus.PROPOSED, "version": 1}), pid="p-dup"))
    assert store.auto_apply("p-dup", CLUB, NOW) is None and "p-dup" in store.pending


def test_cards_and_knowledge_show_the_end_date_or_none() -> None:
    """A person could not tell when a fact stops being true (F-305)."""
    dated = verified(item("kh-dated", valid_to=date(2026, 12, 31)))
    open_ended = verified(item("kh-open"))
    assert views.knowledge(dated, [dated], TODAY)["valid_to"] == "2026-12-31"
    assert views.knowledge(open_ended, [open_ended], TODAY)["valid_to"] is None
    card = views.review_card(proposal(item("kh-card", valid_to=date(2026, 12, 31))), target=open_ended)
    assert card["valid_to"] == "2026-12-31" and card["alternative"]["valid_to"] is None


def test_search_skips_expired_facts_but_learning_can_still_match_them(store: KnowHowStore) -> None:
    """The planner used to find a fact months after its end date (F-304)."""
    old = verified(
        item("kh-old", title="Cafe B notice", statement="Cafe B needs ten days notice", valid_to=date(2020, 1, 1))
    )
    live = verified(
        item("kh-live", title="Cafe B notice now", statement="Cafe B needs ten days notice", valid_to=date(2099, 1, 1))
    )
    store.backend.append(old)
    store.backend.append(live)
    assert [i.item_id for i in store.search(old.club_id, "Cafe B notice")] == ["kh-live"]
    assert {i.item_id for i in store.search(old.club_id, "Cafe B notice", include_expired=True)} == {
        "kh-old",
        "kh-live",
    }
    assert [i.item_id for i in store.search(old.club_id, "Cafe B notice", today=date(2019, 6, 1))].count("kh-old") == 1


def test_the_share_box_is_locked_on_a_replace_card_and_ignored(store) -> None:  # type: ignore[no-untyped-def]
    """The box and label said "shared" while the result kept the old fact's layer (F-310)."""
    known = verified(item("kh-club-fact"))  # a club fact
    new = item("kh-club-fact2", scope=Scope.AUB, club_id=None)
    card = views.review_card(proposal(new, ProposalOp.UPDATE, target_item=known.item_id), target=known)
    assert card["shared"] is False and card["shared_locked"] is True
    fresh = views.review_card(proposal(new))
    assert fresh["shared"] is True and "shared_locked" not in fresh


def test_a_review_card_says_why_it_was_proposed() -> None:
    """The card gave the person the action but not the reason for it (F-311)."""
    p = proposal(item("kh-why"), ProposalOp.MERGE, target_item="kh-known").model_copy(
        update={"rationale": "from an OSA mail; merge: nearly the same words"}
    )
    assert views.review_card(p)["why"] == "from an OSA mail; merge: nearly the same words"


def test_a_rule_card_shows_its_notice_period_so_it_can_be_corrected() -> None:
    """The web edit field starts from the number the planner would enforce (F-309)."""
    from tests.factories import rule

    assert views.review_card(proposal(rule()))["lead_time_days"] == 14
    assert "lead_time_days" not in views.review_card(proposal(item("kh-plain")))
