"""Published HandoverPack -> cabinet screen. No model calls or new permanent writes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NotRequired, TypedDict

from clubops.contracts.handover import HandoverPack, PackStatus
from clubops.contracts.knowhow import KnowHowItem


class SourceView(TypedDict):
    item_id: str
    label: str
    quote: NotRequired[str]


class EntryView(TypedDict):
    text: str
    source: SourceView
    sources: list[SourceView]


class SectionView(TypedDict):
    title: str
    entries: list[EntryView]


class GapView(TypedDict):
    topic: str
    question: str
    ask: str
    look_in: str


class GuideView(TypedDict):
    role: str
    sections: list[SectionView]
    gaps: list[GapView]
    signed_off_at: NotRequired[str]
    signed_off_by: NotRequired[str]


def _source(item: KnowHowItem) -> SourceView:
    result: SourceView = {"item_id": item.item_id, "label": item.title}
    if item.sources[0].quote is not None:
        result["quote"] = item.sources[0].quote
    return result


def guide_view(pack: HandoverPack, items: Sequence[KnowHowItem]) -> GuideView:
    """Keep every real citation; unsupported text becomes a gap, never invented evidence."""
    current = {
        item.item_id: item
        for item in items
        if (item.club_id is None or item.club_id == pack.club_id) and item.is_current(pack.as_of)
    }
    officer = f"Outgoing {pack.role.value.replace('_', ' ')}"
    gaps: list[GapView] = [
        {
            "topic": gap.topic,
            "question": gap.question,
            "ask": officer,
            "look_in": "Review queue"
            if gap.kind.value in {"unverified", "contradiction"}
            else "Club knowledge and source documents",
        }
        for gap in pack.open_gaps
    ]
    sections: list[SectionView] = []
    incomplete = False
    gap_ids = {gap.gap_id for gap in pack.open_gaps}
    for section in pack.sections:
        entries: list[EntryView] = []
        for entry in section.entries:
            if not entry.item_ids or any(item_id not in current for item_id in entry.item_ids):
                if not entry.gap_ids or any(gap_id not in gap_ids for gap_id in entry.gap_ids):
                    incomplete = True
                continue
            sources: list[SourceView] = [_source(current[item_id]) for item_id in dict.fromkeys(entry.item_ids)]
            entries.append({"text": entry.text, "source": sources[0], "sources": sources})
        if entries:
            sections.append({"title": section.section.value.replace("_", " ").capitalize(), "entries": entries})
    if incomplete:
        gaps.append(
            {
                "topic": "An entry needs current approved evidence",
                "question": "Review the supporting knowledge before including this entry in the guide.",
                "ask": officer,
                "look_in": "Review queue",
            }
        )
    result: GuideView = {"role": pack.role.value, "sections": sections, "gaps": gaps}
    if not incomplete and pack.status is PackStatus.SIGNED_OFF and pack.signed_off_at and pack.signed_off_by:
        result["signed_off_at"] = pack.signed_off_at.isoformat()
        result["signed_off_by"] = pack.signed_off_by
    return result
