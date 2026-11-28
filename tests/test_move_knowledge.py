"""T-51: moving approved knowledge between data folders. Synthetic items only."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.move_knowledge import export_items, import_items

from clubops.contracts.knowhow import ItemStatus, Scope
from clubops.knowhow.backends import open_club_store_backend
from tests.factories import item, source

CLUB = "running-club"


def put(data_dir: Path, *items: object) -> None:
    backend = open_club_store_backend(data_dir, CLUB)
    for one in items:
        backend.append(one)  # type: ignore[arg-type]
    backend.close()


def ids(data_dir: Path, club: str = CLUB) -> set[str]:
    backend = open_club_store_backend(data_dir, club)
    found = {i.item_id for i in backend.latest_all()}
    backend.close()
    return found


def approved(item_id: str, **extra: object):
    from datetime import UTC, datetime

    return item(
        item_id,
        status=ItemStatus.VERIFIED,
        verified_by="m-tester",
        verified_at=datetime(2026, 11, 7, tzinfo=UTC),
        **extra,
    )


def test_club_and_shared_items_move_and_a_second_run_adds_nothing(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    shared = approved("kh-shared-form", scope=Scope.AUB, club_id=None)
    put(src, approved("kh-club-a"), approved("kh-club-b"), shared)
    file = tmp_path / "out.jsonl"
    assert export_items(CLUB, src, file) == (3, 3)
    assert import_items(CLUB, dst, file) == (3, 0)
    assert ids(dst) == {"kh-club-a", "kh-club-b", "kh-shared-form"}
    assert import_items(CLUB, dst, file) == (0, 3)  # rerun is harmless


def test_every_version_comes_along_and_an_existing_item_is_never_overwritten(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    first = approved("kh-club-a")
    second = approved("kh-club-a", version=2, statement="Book Green Field four weeks ahead through the form.")
    put(src, first, second)
    put(dst, approved("kh-club-a", statement="The host's own wording stays untouched."))
    file = tmp_path / "out.jsonl"
    export_items(CLUB, src, file)
    assert len(file.read_text().splitlines()) == 2
    assert import_items(CLUB, dst, file) == (0, 1)
    backend = open_club_store_backend(dst, CLUB)
    assert backend.versions("kh-club-a")[0].statement.startswith("The host's own wording")
    backend.close()


def test_another_clubs_items_are_not_exported_and_a_file_holding_them_is_refused(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    other = approved("kh-other-club", club_id="asme", sources=[source("synthetic-asme-1")])
    mine = approved("kh-club-a")
    backend = open_club_store_backend(src, "asme")
    backend.append(other)
    backend.close()
    put(src, mine)
    file = tmp_path / "out.jsonl"
    assert export_items(CLUB, src, file) == (1, 1)  # only the running club's item
    file.write_text(file.read_text() + other.model_dump_json() + "\n")
    with pytest.raises(SystemExit):
        import_items(CLUB, dst, file)
    assert ids(dst) == set()  # nothing was imported


def test_dry_run_counts_but_writes_nothing(tmp_path: Path) -> None:
    src, dst = tmp_path / "src", tmp_path / "dst"
    put(src, approved("kh-club-a"))
    file = tmp_path / "out.jsonl"
    export_items(CLUB, src, file)
    assert import_items(CLUB, dst, file, dry_run=True) == (1, 0)
    assert ids(dst) == set()
