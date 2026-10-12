"""Handover packs: complete, cited, role-specific and reproducible."""

from __future__ import annotations

from datetime import date, timedelta

from clubops.contracts.common import Role
from clubops.contracts.handover import HandoverRequest, Section
from clubops.contracts.knowhow import GapKind, GapRequest, VerifyDecision, VerifyRequest
from clubops.knowhow.gaps import deterministic_gaps
from clubops.knowhow.handover import build_handover
from clubops.knowhow.store import KnowHowStore
from tests.factories import CLUB, NOW, TODAY, actor, item, proposal, rule


def seeded() -> KnowHowStore:
    store = KnowHowStore()
    items = [
        item(),
        item(
            "kh-water-sponsor",
            title="Water sponsor",
            statement="A local supplier has given water for our runs.",
            details={
                "kind": "relationship",
                "party_name": "Synthetic Water Co",
                "party_type": "sponsor",
                "offers": ["water"],
            },
            tags=["sponsors"],
        ),
        item(
            "kh-semester-report",
            title="Semester report to OSA",
            statement="OSA expects a semester activity report.",
            details={"kind": "obligation", "owed_to": "OSA", "due_rule": "last week of each semester"},
            tags=[],
        ),
        rule(),
    ]
    for n, it in enumerate(items):
        p = proposal(it, pid=f"p-{n}")
        store.submit(p)
        store.verify(VerifyRequest(proposal=p, decision=VerifyDecision.ACCEPT), actor(Role.PRESIDENT), NOW)
    store.submit(proposal(item("kh-unverified", title="Unverified tip", statement="Ask OSA in person."), pid="p-open"))
    return store


def request(role: Role = Role.PRESIDENT) -> HandoverRequest:
    return HandoverRequest(club_id=CLUB, role=role, outgoing="m-outgoing", as_of=TODAY)


def test_president_pack_has_every_section_with_content() -> None:
    pack = build_handover(seeded(), request())
    assert {s.section for s in pack.sections} == {
        Section.OPEN_OBLIGATIONS,
        Section.PROCEDURES,
        Section.RELATIONSHIPS,
        Section.RULES,
        Section.OPEN_QUESTIONS,
    }


def test_every_entry_is_cited() -> None:
    pack = build_handover(seeded(), request())
    assert all(e.item_ids or e.gap_ids for s in pack.sections for e in s.entries)


def test_unverified_know_how_never_appears_as_fact() -> None:
    pack = build_handover(seeded(), request())
    facts = [e for s in pack.sections if s.section is not Section.OPEN_QUESTIONS for e in s.entries]
    assert all("kh-unverified" not in e.item_ids for e in facts)
    assert any(g.kind is GapKind.UNVERIFIED for g in pack.open_gaps)


def test_gaps_flag_missing_contact_and_unowned_obligation() -> None:
    kinds = {g.kind for g in deterministic_gaps(seeded(), GapRequest(club_id=CLUB, as_of=TODAY)).gaps}
    assert {GapKind.MISSING, GapKind.UNOWNED_OBLIGATION, GapKind.UNVERIFIED} <= kinds


def test_stale_items_are_flagged() -> None:
    later = TODAY + timedelta(days=400)
    gaps = deterministic_gaps(seeded(), GapRequest(club_id=CLUB, as_of=later)).gaps
    assert any(g.kind is GapKind.STALE for g in gaps)


def test_sponsorship_pack_is_scoped_to_its_role() -> None:
    pack = build_handover(seeded(), request(Role.SPONSORSHIP))
    cited = {i for s in pack.sections for e in s.entries for i in e.item_ids}
    assert "kh-water-sponsor" in cited
    assert "kh-book-green-field" not in cited


def test_pack_is_reproducible() -> None:
    assert build_handover(seeded(), request()).content_sha256() == build_handover(seeded(), request()).content_sha256()


def test_other_clubs_know_how_is_not_included() -> None:
    pack = build_handover(
        seeded(),
        HandoverRequest(club_id="other-club", role=Role.PRESIDENT, outgoing="m-other", as_of=date(2026, 10, 5)),
    )
    cited = {i for s in pack.sections for e in s.entries for i in e.item_ids}
    assert cited == {"kh-rule-guests"}  # AUB-wide rules are shared; club know-how is not
