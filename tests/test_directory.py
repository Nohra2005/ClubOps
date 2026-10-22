"""Contacts, assets and event history: shared vs club files, restart, club separation. Synthetic data."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from clubops.capabilities.runner import CapabilityError
from clubops.contracts.common import ErrorCode
from clubops.contracts.directory import Asset, AssetKind, Contact
from clubops.contracts.event import EventRecord, EventStatus
from clubops.knowhow.directory import Directory


@pytest.fixture
def ours(tmp_path: Path) -> Iterator[Directory]:
    d = Directory(tmp_path, "running-club")
    yield d
    d.close()


def office() -> Contact:
    return Contact(contact_id="ct-osa", club_id=None, name="Student Activities", organization="OSA")


def cafe() -> Contact:
    return Contact(contact_id="ct-cafe", club_id="running-club", name="Cafe manager", organization="Cafe C")


def event(event_id: str, on: date) -> EventRecord:
    return EventRecord(event_id=event_id, club_id="running-club", title="Run", on=on, status=EventStatus.DONE)


def test_shared_contacts_are_seen_by_every_club_but_club_contacts_are_not(tmp_path: Path, ours: Directory) -> None:
    ours.put_contact(office())
    ours.put_contact(cafe())
    assert [c.contact_id for c in ours.contacts()] == ["ct-osa", "ct-cafe"]

    theirs = Directory(tmp_path, "asme")
    try:
        assert [c.contact_id for c in theirs.contacts()] == ["ct-osa"]
    finally:
        theirs.close()


def test_a_club_cannot_write_another_clubs_entries(ours: Directory) -> None:
    other = Contact(contact_id="ct-someone", club_id="asme", name="Someone", organization="ASME")
    with pytest.raises(CapabilityError) as exc:
        ours.put_contact(other)
    assert exc.value.code is ErrorCode.NOT_AUTHORIZED


def test_events_survive_a_restart_and_come_newest_first(tmp_path: Path, ours: Directory) -> None:
    ours.put_event(event("ev-old", date(2025, 4, 10)))
    ours.put_event(event("ev-new", date(2026, 10, 7)))
    ours.close()

    again = Directory(tmp_path, "running-club")
    try:
        assert [e.event_id for e in again.events()] == ["ev-new", "ev-old"]
        found = again.event("ev-old")
        assert found is not None and found.on == date(2025, 4, 10)
        assert again.event("ev-missing") is None
    finally:
        again.close()


def test_saving_again_updates_instead_of_duplicating(ours: Directory) -> None:
    ours.put_event(event("ev-run", date(2026, 10, 7)))
    closed = event("ev-run", date(2026, 10, 7)).model_copy(update={"status": EventStatus.CLOSED, "outcome": "ok"})
    ours.put_event(EventRecord.model_validate(closed.model_dump()))
    assert [e.status for e in ours.events()] == [EventStatus.CLOSED]


def test_assets_are_stored_with_their_official_flag(ours: Directory) -> None:
    logo = Asset(
        asset_id="as-club-logo",
        club_id="running-club",
        name="Club logo",
        kind=AssetKind.LOGO,
        owner="Running Club",
        official=True,
        file_ref="assets/club-logo.svg",
        vector=True,
    )
    ours.put_asset(logo)
    assert ours.assets() == [logo]
