"""Deterministic handover assembly. The model's part (interviewing, summarizing) feeds the
knowledge base upstream; the pack itself is a reproducible view of verified know-how."""

from __future__ import annotations

from clubops.contracts.handover import HandoverEntry, HandoverPack, HandoverRequest, HandoverSection, Section
from clubops.contracts.knowhow import GapRequest, Kind, KnowHowItem
from clubops.knowhow.gaps import deterministic_gaps, relevant_to
from clubops.knowhow.store import KnowHowStore

SECTION_OF: dict[Kind, Section] = {
    Kind.OBLIGATION: Section.OPEN_OBLIGATIONS,
    Kind.RHYTHM: Section.YEAR_AT_A_GLANCE,
    Kind.PROCEDURE: Section.PROCEDURES,
    Kind.GOTCHA: Section.PROCEDURES,
    Kind.RELATIONSHIP: Section.RELATIONSHIPS,
    Kind.LESSON: Section.LESSONS,
    Kind.DECISION: Section.DECISIONS,
    Kind.IDENTITY: Section.IDENTITY,
    Kind.RULE: Section.RULES,
}


def _entry(item: KnowHowItem) -> HandoverEntry:
    confirmed = item.last_confirmed_at or item.verified_at
    return HandoverEntry(
        text=f"{item.title}: {item.statement}"[:600],
        item_ids=[item.item_id],
        last_confirmed=confirmed.date() if confirmed else None,
    )


def build_handover(store: KnowHowStore, request: HandoverRequest) -> HandoverPack:
    items = [i for i in store.current(request.club_id, request.as_of) if relevant_to(i, request.role)]
    gaps = deterministic_gaps(store, GapRequest(club_id=request.club_id, role=request.role, as_of=request.as_of)).gaps

    sections: list[HandoverSection] = []
    for section in Section:
        if section is Section.OPEN_QUESTIONS:
            entries = [HandoverEntry(text=g.question, gap_ids=[g.gap_id]) for g in gaps]
        else:
            entries = [_entry(i) for i in items if SECTION_OF[i.kind] is section]
        if entries:
            sections.append(HandoverSection(section=section, entries=entries))

    return HandoverPack(
        pack_id=f"{request.club_id}-{request.role.value.replace('_', '-')}-{request.as_of.isoformat()}",
        club_id=request.club_id,
        role=request.role,
        as_of=request.as_of,
        version=1,
        sections=sections,
        open_gaps=gaps,
    )
