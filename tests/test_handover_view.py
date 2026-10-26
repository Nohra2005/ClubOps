"""Synthetic public-contract fixtures for Christophe's handover screen adapter."""

from clubops.api.handover import guide_view
from clubops.contracts.common import Role
from clubops.contracts.handover import HandoverEntry, HandoverPack, HandoverSection, Section
from clubops.contracts.knowhow import Gap, GapKind
from tests.factories import CLUB, TODAY, item, verified


def pack(*entries: HandoverEntry, gaps: list[Gap] | None = None) -> HandoverPack:
    return HandoverPack(
        pack_id="pack-synthetic",
        club_id=CLUB,
        role=Role.EVENTS,
        as_of=TODAY,
        version=1,
        sections=[HandoverSection(section=Section.PROCEDURES, entries=list(entries))],
        open_gaps=gaps or [],
    )


def test_empty_guide_has_no_invented_sources_or_signoff() -> None:
    assert guide_view(pack(), []) == {"role": "events", "sections": [], "gaps": []}


def test_every_current_approved_citation_is_retained() -> None:
    first, second = verified(item()), verified(item("kh-second-example"))
    entry = HandoverEntry(
        text="Synthetic instructions with two supporting facts.", item_ids=[first.item_id, second.item_id]
    )
    result = guide_view(pack(entry), [first, second])
    rendered = result["sections"][0]["entries"][0]
    assert [source["item_id"] for source in rendered["sources"]] == [first.item_id, second.item_id]
    assert rendered["source"] == rendered["sources"][0]


def test_foreign_unverified_and_expired_items_never_appear_in_the_guide() -> None:
    foreign = verified(item(club_id="asme", title="PRIVATE foreign lesson"))
    entry = HandoverEntry(text="PRIVATE unsupported instructions", item_ids=[foreign.item_id])
    for unsupported in [foreign, item(), verified(item(valid_to=TODAY.replace(year=TODAY.year - 1)))]:
        result = guide_view(pack(entry), [unsupported])
        assert result["sections"] == []
        assert len(result["gaps"]) == 1
        assert "PRIVATE" not in str(result)


def test_gap_only_entries_remain_questions_without_fake_knowledge_links() -> None:
    gap = Gap(
        gap_id="gap-example",
        kind=GapKind.MISSING,
        topic="Synthetic missing process",
        question="Who owns this task?",
        priority="high",
    )
    result = guide_view(pack(HandoverEntry(text=gap.question, gap_ids=[gap.gap_id]), gaps=[gap]), [])
    assert result["sections"] == []
    assert result["gaps"][0]["question"] == gap.question
    assert result["gaps"][0]["ask"] == "Outgoing events"
