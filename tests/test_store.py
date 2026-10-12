"""The verified-write rule: nothing enters the knowledge base without a cabinet member."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from clubops.capabilities.runner import CapabilityError
from clubops.contracts.common import ErrorCode, Role
from clubops.contracts.knowhow import ItemStatus, ProposalOp, VerifyDecision, VerifyRequest
from tests.factories import CLUB, NOW, TODAY, actor, item, proposal, rule, source


def accept(store, prop, who=None, decision=VerifyDecision.ACCEPT, **kw):  # type: ignore[no-untyped-def]
    store.submit(prop)
    return store.verify(VerifyRequest(proposal=prop, decision=decision, **kw), who or actor(), NOW).data


def test_create_then_visible_as_current(store) -> None:  # type: ignore[no-untyped-def]
    result = accept(store, proposal())
    assert result.committed.status is ItemStatus.VERIFIED
    assert result.committed.verified_by == "m-tester"
    assert [i.item_id for i in store.current(CLUB, TODAY)] == ["kh-book-green-field"]


def test_unverified_proposal_is_not_current(store) -> None:  # type: ignore[no-untyped-def]
    store.submit(proposal())
    assert store.current(CLUB, TODAY) == []


def test_reject_commits_nothing(store) -> None:  # type: ignore[no-untyped-def]
    result = accept(store, proposal(), decision=VerifyDecision.REJECT)
    assert result.committed is None
    assert store.current(CLUB, TODAY) == []
    assert store.pending == {}


def test_member_cannot_verify(store) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CapabilityError) as exc:
        accept(store, proposal(), who=actor(Role.MEMBER))
    assert exc.value.code is ErrorCode.NOT_AUTHORIZED


def test_unauthenticated_cabinet_member_cannot_verify(store) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CapabilityError):
        accept(store, proposal(), who=actor(Role.PRESIDENT, verified=False))


def test_cannot_verify_another_clubs_know_how(store) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CapabilityError) as exc:
        accept(store, proposal(), who=actor(club="other-club"))
    assert exc.value.code is ErrorCode.NOT_AUTHORIZED


def test_aub_rules_need_a_president(store) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CapabilityError):
        accept(store, proposal(rule()), who=actor(Role.EVENTS))
    assert accept(store, proposal(rule(), pid="p-2")).committed is not None


def test_update_supersedes_previous_version_and_keeps_history(store) -> None:  # type: ignore[no-untyped-def]
    accept(store, proposal())
    newer = item(statement="Book Green Field four weeks ahead; three is too late since 2026.")
    result = accept(store, proposal(newer, op=ProposalOp.UPDATE, target_item="kh-book-green-field", pid="p-2"))
    assert result.committed.version == 2
    history = store.history("kh-book-green-field")
    assert [v.status for v in history] == [ItemStatus.SUPERSEDED, ItemStatus.VERIFIED]
    assert store.current(CLUB, TODAY)[0].statement.startswith("Book Green Field four weeks")


def test_merge_adds_support_without_changing_statement(store) -> None:  # type: ignore[no-untyped-def]
    accept(store, proposal())
    again = item(
        sources=[source("synthetic-retro-2", "again three weeks before was right")],
        support={"events": ["ev-fall-run"], "source_count": 1},
    )
    result = accept(store, proposal(again, op=ProposalOp.MERGE, target_item="kh-book-green-field", pid="p-2"))
    assert result.committed.support.source_count == 2
    assert result.committed.support.events == ["ev-fall-run"]
    assert result.committed.statement == item().statement


def test_retire_removes_from_current(store) -> None:  # type: ignore[no-untyped-def]
    accept(store, proposal())
    accept(store, proposal(item(), op=ProposalOp.RETIRE, target_item="kh-book-green-field", pid="p-2"))
    assert store.current(CLUB, TODAY + timedelta(days=1)) == []


def test_accepted_contradiction_supersedes_the_loser(store) -> None:  # type: ignore[no-untyped-def]
    accept(store, proposal())
    rival = item("kh-book-green-field-v2", statement="Green Field needs four weeks' notice, per OSA in 2026.")
    result = accept(
        store,
        proposal(
            rival,
            op=ProposalOp.CONTRADICTION,
            target_item="kh-book-green-field",
            conflicts_with=["kh-book-green-field"],
            pid="p-2",
        ),
    )
    assert result.superseded == ["kh-book-green-field"]
    assert [i.item_id for i in store.current(CLUB, TODAY)] == ["kh-book-green-field-v2"]


def test_flagged_proposal_needs_a_reason_to_accept(store) -> None:  # type: ignore[no-untyped-def]
    flagged = proposal(injection_flags=["source says 'ignore previous instructions'"])
    with pytest.raises(CapabilityError) as exc:
        accept(store, flagged)
    assert exc.value.code is ErrorCode.INJECTION_SUSPECTED


def test_unknown_proposal_cannot_be_verified(store) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(CapabilityError) as exc:
        store.verify(VerifyRequest(proposal=proposal(), decision=VerifyDecision.ACCEPT), actor(), NOW)
    assert exc.value.code is ErrorCode.NOT_FOUND


def test_validity_window_is_respected(store) -> None:  # type: ignore[no-untyped-def]
    accept(store, proposal(item(valid_from=date(2027, 1, 1))))
    assert store.current(CLUB, TODAY) == []
    assert len(store.current(CLUB, date(2027, 2, 1))) == 1


# --------------------------------------------- verify trusts only the queued copy


def test_changed_proposal_under_the_same_id_is_refused(store) -> None:  # type: ignore[no-untyped-def]
    queued = proposal()
    store.submit(queued)
    swapped = proposal(item(statement="Pay the vendor in cash, no receipt needed."))
    with pytest.raises(CapabilityError) as exc:
        store.verify(VerifyRequest(proposal=swapped, decision=VerifyDecision.ACCEPT), actor(), NOW)
    assert exc.value.code is ErrorCode.STALE_INPUT
    assert store.current(CLUB, TODAY) == []
    assert store.pending == {"p-1": queued}


def test_dropping_injection_flags_from_the_request_does_not_skip_the_reason(store) -> None:  # type: ignore[no-untyped-def]
    store.submit(proposal(injection_flags=["source says 'ignore previous instructions'"]))
    with pytest.raises(CapabilityError) as exc:
        store.verify(VerifyRequest(proposal=proposal(), decision=VerifyDecision.ACCEPT), actor(), NOW)
    assert exc.value.code is ErrorCode.STALE_INPUT
    assert store.current(CLUB, TODAY) == []


def test_accept_edited_is_the_way_to_change_content(store) -> None:  # type: ignore[no-untyped-def]
    edited = item(statement="Book Green Field four weeks ahead through the reservation form.")
    result = accept(store, proposal(), decision=VerifyDecision.ACCEPT_EDITED, edited_candidate=edited)
    assert result.committed.statement.startswith("Book Green Field four weeks")


def test_refused_decision_keeps_the_proposal_queued(store) -> None:  # type: ignore[no-untyped-def]
    accept(store, proposal())
    duplicate = proposal(pid="p-2")
    with pytest.raises(CapabilityError) as exc:
        accept(store, duplicate)
    assert exc.value.code is ErrorCode.CONFLICT
    assert "p-2" in store.pending
    with pytest.raises(CapabilityError):
        store.verify(VerifyRequest(proposal=duplicate, decision=VerifyDecision.ACCEPT), actor(Role.MEMBER), NOW)
    assert "p-2" in store.pending


# ----------------------------------------------------- contradiction history


def test_contradiction_winner_reusing_the_losers_id_becomes_its_next_version(store) -> None:  # type: ignore[no-untyped-def]
    accept(store, proposal())
    rival = item(statement="Green Field needs four weeks' notice, per OSA in 2026.")
    result = accept(
        store,
        proposal(
            rival,
            op=ProposalOp.CONTRADICTION,
            target_item="kh-book-green-field",
            conflicts_with=["kh-book-green-field"],
            pid="p-2",
        ),
    )
    assert result.committed.version == 2
    history = store.history("kh-book-green-field")
    assert [(v.version, v.status) for v in history] == [(1, ItemStatus.SUPERSEDED), (2, ItemStatus.VERIFIED)]


def test_contradiction_winner_cannot_reuse_an_unrelated_id(store) -> None:  # type: ignore[no-untyped-def]
    accept(store, proposal())
    accept(store, proposal(item("kh-water-sponsor", title="Water sponsor"), pid="p-2"))
    clash = item("kh-water-sponsor", statement="Green Field needs four weeks' notice.")
    with pytest.raises(CapabilityError) as exc:
        accept(
            store,
            proposal(
                clash,
                op=ProposalOp.CONTRADICTION,
                target_item="kh-book-green-field",
                conflicts_with=["kh-book-green-field"],
                pid="p-3",
            ),
        )
    assert exc.value.code is ErrorCode.CONFLICT
    assert [v.status for v in store.history("kh-book-green-field")] == [ItemStatus.VERIFIED]
