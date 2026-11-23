"""One e-mail can be fetched and read again, with backups and a dry run first (F-244)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from clubops.inbox.capture import PendingInbox
from clubops.inbox.guards import InboxLedger
from clubops.inbox_intake import InboxNotes
from clubops.inbox_reset import forget_read
from tests.test_inbox_routes import CLUB, _fetch, _mail

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


def _read_once(data: Path) -> str:
    _fetch(data, {"m1": _mail(CLUB, "Campus access")})
    notes = InboxNotes(data / "inbox-notes.db")
    fingerprint = notes.fingerprint("m1", CLUB)
    assert fingerprint
    ledger = InboxLedger(data / "inbox-ledger.db")
    token = ledger.claim_read(fingerprint)
    assert token
    ledger.mark_read(fingerprint, token)
    PendingInbox(data / "inbox.db").mark_processed("m1", CLUB)
    return fingerprint


def test_a_dry_run_changes_nothing(tmp_path: Path) -> None:
    fingerprint = _read_once(tmp_path)
    report = forget_read(tmp_path, "m1", apply=False)
    assert "Dry run" in report[-1]
    assert InboxLedger(tmp_path / "inbox-ledger.db").was_read(fingerprint)
    assert not (tmp_path / "backups").exists()


def test_applying_backs_up_then_lets_the_next_fetch_queue_it_again(tmp_path: Path) -> None:
    fingerprint = _read_once(tmp_path)
    report = forget_read(tmp_path, "m1", apply=True, now=NOW)
    assert any("Backups" in line for line in report)
    [backup] = list((tmp_path / "backups").iterdir())
    assert sorted(p.name for p in backup.iterdir()) == ["inbox-ledger.db", "inbox-notes.db", "inbox.db"]
    assert not InboxLedger(tmp_path / "inbox-ledger.db").was_read(fingerprint)
    counts = _fetch(tmp_path, {"m1": _mail(CLUB, "Campus access")})
    assert counts["queued"] == 1  # back in the waiting list, ready for a new read
    with closing(sqlite3.connect(backup / "inbox-ledger.db")) as old:  # the backup still holds the old mark
        assert old.execute("SELECT state FROM read_mail").fetchone() == ("read",)


def test_an_unknown_email_or_missing_files_change_nothing(tmp_path: Path) -> None:
    assert "Not found" in forget_read(tmp_path, "m1", apply=True)[0]
    _read_once(tmp_path)
    assert "never accepted" in forget_read(tmp_path, "nope", apply=True)[0]
    assert not (tmp_path / "backups").exists()
