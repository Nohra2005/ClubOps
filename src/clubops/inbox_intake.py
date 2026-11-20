"""Free intake of forwarded OSA mail (T-47, D-114): every check runs before any paid read.

Fetch: the club tag and cabinet sender (J-10), then J-22's forward check (verified sender, original
sender on the private OSA list, cleaned text, read-once fingerprint). Accepted mail waits for a person's
click with only the cleaned text; skipped mail is noted with its reason. No model call happens here.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Collection, Mapping
from contextlib import closing
from datetime import datetime
from pathlib import Path

from clubops.contracts.common import Untrusted
from clubops.contracts.knowhow import CaptureRequest
from clubops.inbox.capture import PendingInbox, capture_email
from clubops.inbox.gmail import MailGateway
from clubops.inbox.guards import InboxLedger, check_forward

SKIP_TEXT = {
    "wrong_club_tag": "not sent to this club's ClubOps address",
    "unverified_sender": "not forwarded by a verified cabinet address",
    "missing_forward_headers": "not a forwarded e-mail",
    "malformed_forward_headers": "the forwarded e-mail's header lines could not be read",
    "original_sender_not_osa": "ClubOps only reads e-mails forwarded from OSA staff",
    "empty_forward": "the forwarded e-mail has no text",
    "already_read": "already read for another club",
}


class InboxNotes:
    """Per-message notes next to the queue: the read-once fingerprint, or why the e-mail was skipped."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS accepted (message_id TEXT PRIMARY KEY, club_id TEXT NOT NULL, "
                "fingerprint TEXT NOT NULL, audience INTEGER)"
            )
            if "audience" not in {row[1] for row in db.execute("PRAGMA table_info(accepted)")}:
                db.execute("ALTER TABLE accepted ADD COLUMN audience INTEGER")  # notes made before D-126
            db.execute(
                "CREATE TABLE IF NOT EXISTS skipped (message_id TEXT PRIMARY KEY, club_id TEXT NOT NULL, "
                "reason TEXT NOT NULL, subject TEXT NOT NULL)"
            )

    def seen(self, message_id: str) -> bool:
        with closing(sqlite3.connect(self.path)) as db:
            return any(
                db.execute(f"SELECT 1 FROM {table} WHERE message_id=?", (message_id,)).fetchone()  # noqa: S608
                for table in ("accepted", "skipped")
            )

    def accept(self, message_id: str, club_id: str, fingerprint: str, audience: int | None = None) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT OR IGNORE INTO accepted (message_id, club_id, fingerprint, audience) VALUES (?, ?, ?, ?)",
                (message_id, club_id, fingerprint, audience),
            )

    def audience(self, message_id: str, club_id: str) -> int | None:
        """How many people the original went to, or None when it was not visible."""
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(
                "SELECT audience FROM accepted WHERE message_id=? AND club_id=?", (message_id, club_id)
            ).fetchone()
        return int(row[0]) if row and row[0] is not None else None

    def skip(self, message_id: str, club_id: str, reason: str, subject: str) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR IGNORE INTO skipped VALUES (?, ?, ?, ?)", (message_id, club_id, reason, subject))

    def fingerprint(self, message_id: str, club_id: str) -> str | None:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(
                "SELECT fingerprint FROM accepted WHERE message_id=? AND club_id=?", (message_id, club_id)
            ).fetchone()
        return str(row[0]) if row else None

    def skipped(self, club_id: str) -> list[dict[str, str]]:
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute(
                "SELECT message_id, subject, reason FROM skipped WHERE club_id=? ORDER BY rowid", (club_id,)
            ).fetchall()
        return [{"id": m, "subject": s, "reason": r, "why": SKIP_TEXT.get(r, r)} for m, s, r in rows]


def _cleaned(request: CaptureRequest, content: str) -> CaptureRequest:
    """Keep the forwarder, date and subject lines; replace the raw body with J-22's cleaned text."""
    source = request.sources[0]
    head = [line for line in source.content.splitlines()[:3] if line.startswith(("Forwarded by:", "Date:", "Subject:"))]
    return CaptureRequest(
        club_id=request.club_id,
        sources=[Untrusted(content="\n".join([*head, f"Body: {content}"]), source=source.source)],
    )


def intake(
    gateway: MailGateway,
    queue: PendingInbox,
    *,
    notes: InboxNotes,
    ledger: InboxLedger,
    cabinet: Mapping[str, set[str]],
    osa_senders: Collection[str],
    received_at: datetime,
) -> dict[str, int]:
    """Queue only mail that passed every free check; note the reason for everything else."""
    senders = {club: set(addresses) | ledger.verified_senders(club) for club, addresses in cabinet.items()}
    counts = {"queued": 0, "skipped": 0, "not_for_a_club": 0}
    for message_id in gateway.list_ids():
        if notes.seen(message_id):
            continue
        raw = gateway.get_raw(message_id)
        request = capture_email(raw, message_id, senders, received_at)
        if request is None:
            counts["not_for_a_club"] += 1
            continue
        checked = check_forward(raw, request.club_id, senders[request.club_id], osa_senders, ledger)
        if checked.reason is not None:
            subject = next((x[9:] for x in request.sources[0].content.splitlines() if x.startswith("Subject: ")), "")
            notes.skip(message_id, request.club_id, checked.reason, subject[:200])
            counts["skipped"] += 1
            continue
        if queue.enqueue(message_id, _cleaned(request, checked.content)):
            notes.accept(message_id, request.club_id, checked.fingerprint, checked.audience)
            counts["queued"] += 1
    return counts


def parse_osa_senders(value: str | None) -> set[str]:
    """``a@x, b@y`` from the private .env (``CLUBOPS_OSA_SENDERS``); never committed."""
    return {a.strip().casefold() for a in (value or "").split(",") if "@" in a}
