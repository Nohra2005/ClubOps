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
            # An e-mail refused only because its sender is not on the OSA list is kept here, already cleaned, so a
            # cabinet member can release it with one click (D-136). Never read by a model until then.
            db.execute(
                "CREATE TABLE IF NOT EXISTS held (message_id TEXT PRIMARY KEY, club_id TEXT NOT NULL, "
                "request TEXT NOT NULL, fingerprint TEXT NOT NULL, audience INTEGER)"
            )
            if "unlisted" not in {row[1] for row in db.execute("PRAGMA table_info(accepted)")}:
                db.execute("ALTER TABLE accepted ADD COLUMN unlisted INTEGER NOT NULL DEFAULT 0")

    def seen(self, message_id: str) -> bool:
        with closing(sqlite3.connect(self.path)) as db:
            return any(
                db.execute(f"SELECT 1 FROM {table} WHERE message_id=?", (message_id,)).fetchone()  # noqa: S608
                for table in ("accepted", "skipped")
            )

    def accept(
        self, message_id: str, club_id: str, fingerprint: str, audience: int | None = None, unlisted: bool = False
    ) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT OR IGNORE INTO accepted (message_id, club_id, fingerprint, audience, unlisted) "
                "VALUES (?, ?, ?, ?, ?)",
                (message_id, club_id, fingerprint, audience, int(unlisted)),
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

    def unknown_audience(self, message_id: str) -> tuple[str, str] | None:
        """(club, fingerprint) of an accepted message whose audience was never counted (checked before D-126)."""
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(
                "SELECT club_id, fingerprint FROM accepted WHERE message_id=? AND audience IS NULL", (message_id,)
            ).fetchone()
        return (str(row[0]), str(row[1])) if row else None

    def backfill_audience(self, message_id: str, club_id: str, fingerprint: str, audience: int) -> bool:
        """Fill in a missing count, only for the same checked message (same fingerprint) and never over a count."""
        with closing(sqlite3.connect(self.path)) as db, db:
            cursor = db.execute(
                "UPDATE accepted SET audience=? "
                "WHERE message_id=? AND club_id=? AND fingerprint=? AND audience IS NULL",
                (audience, message_id, club_id, fingerprint),
            )
        return cursor.rowcount == 1

    def fingerprint(self, message_id: str, club_id: str) -> str | None:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(
                "SELECT fingerprint FROM accepted WHERE message_id=? AND club_id=?", (message_id, club_id)
            ).fetchone()
        return str(row[0]) if row else None

    def hold(
        self, message_id: str, club_id: str, request: CaptureRequest, fingerprint: str, audience: int | None
    ) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT OR IGNORE INTO held VALUES (?, ?, ?, ?, ?)",
                (message_id, club_id, request.model_dump_json(), fingerprint, audience),
            )

    def take_held(self, message_id: str, club_id: str) -> tuple[CaptureRequest, str, int | None] | None:
        """Remove and return a held e-mail of this club, or None. The skipped line goes with it."""
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute(
                "SELECT request, fingerprint, audience FROM held WHERE message_id=? AND club_id=?",
                (message_id, club_id),
            ).fetchone()
            if row is None:
                return None
            db.execute("DELETE FROM held WHERE message_id=?", (message_id,))
            db.execute("DELETE FROM skipped WHERE message_id=?", (message_id,))
        return CaptureRequest.model_validate_json(row[0]), str(row[1]), (int(row[2]) if row[2] is not None else None)

    def unheld_unlisted(self, message_id: str) -> str | None:
        """The club of a mail skipped only for its sender whose cleaned text is not kept yet (skipped before D-136)."""
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(
                "SELECT club_id FROM skipped WHERE message_id=? AND reason='original_sender_not_osa' "
                "AND message_id NOT IN (SELECT message_id FROM held)",
                (message_id,),
            ).fetchone()
        return str(row[0]) if row else None

    def is_unlisted(self, message_id: str, club_id: str) -> bool:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(
                "SELECT unlisted FROM accepted WHERE message_id=? AND club_id=?", (message_id, club_id)
            ).fetchone()
        return bool(row and row[0])

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
    counts = {"queued": 0, "skipped": 0, "not_for_a_club": 0, "refreshed": 0}
    waiting = {message_id for club in cabinet for message_id, _ in queue.pending(club)}
    for message_id in gateway.list_ids():
        if notes.seen(message_id):
            unheld = notes.unheld_unlisted(message_id)
            if unheld is not None:  # skipped before "read anyway" existed: keep its cleaned text now (free)
                raw = gateway.get_raw(message_id)
                held_request = capture_email(raw, message_id, senders, received_at)
                if held_request is not None and held_request.club_id == unheld:
                    kept = check_forward(raw, unheld, senders[unheld], osa_senders, ledger, allow_unlisted_sender=True)
                    if kept.reason is None:
                        notes.hold(
                            message_id, unheld, _cleaned(held_request, kept.content), kept.fingerprint, kept.audience
                        )
                continue
            # A message checked before the audience count existed and still waiting gets its count now: re-run the
            # free checks on the same mail and fill in only the number. Read, skipped and changed mail is left alone.
            old = notes.unknown_audience(message_id) if message_id in waiting else None
            if old is not None:
                raw = gateway.get_raw(message_id)
                again = capture_email(raw, message_id, senders, received_at)
                if again is not None and again.club_id == old[0]:
                    checked = check_forward(raw, again.club_id, senders[again.club_id], osa_senders, ledger)
                    same_mail = checked.fingerprint == old[1]  # only the mail that was checked before
                    if checked.reason is None and checked.audience is not None and same_mail:
                        counts["refreshed"] += int(
                            notes.backfill_audience(message_id, old[0], old[1], checked.audience)
                        )
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
            if checked.reason == "original_sender_not_osa":
                # Every other check passes too? Then keep the cleaned text so one click can release it (D-136).
                released = check_forward(
                    raw, request.club_id, senders[request.club_id], osa_senders, ledger, allow_unlisted_sender=True
                )
                if released.reason is None:
                    notes.hold(
                        message_id,
                        request.club_id,
                        _cleaned(request, released.content),
                        released.fingerprint,
                        released.audience,
                    )
            counts["skipped"] += 1
            continue
        if queue.enqueue(message_id, _cleaned(request, checked.content)):
            notes.accept(message_id, request.club_id, checked.fingerprint, checked.audience)
            counts["queued"] += 1
    return counts


def parse_osa_senders(value: str | None) -> set[str]:
    """``a@x, b@y`` from the private .env (``CLUBOPS_OSA_SENDERS``); never committed."""
    return {a.strip().casefold() for a in (value or "").split(",") if "@" in a}
