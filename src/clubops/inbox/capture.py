"""Route cabinet-forwarded mail to the right club's pending capture queue."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping
from datetime import datetime
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

from clubops.contracts.common import SourceKind, SourceRef, Untrusted
from clubops.contracts.knowhow import CaptureRequest

_TAG = re.compile(r"^clubops\.inbox\+([a-z0-9-]+)@gmail\.com$", re.IGNORECASE)


def capture_email(
    raw: bytes, message_id: str, cabinet_senders: Mapping[str, set[str]], received_at: datetime
) -> CaptureRequest | None:
    """Reject unknown clubs and non-cabinet senders before making an Untrusted source."""
    mail = BytesParser(policy=policy.default).parsebytes(raw)
    sender_addresses = [addr.casefold() for _, addr in getaddresses(mail.get_all("From", []))]
    recipients = [addr.casefold() for _, addr in getaddresses(mail.get_all("To", []))]
    if len(sender_addresses) != 1:
        return None
    clubs = {match.group(1) for recipient in recipients if (match := _TAG.fullmatch(recipient))}
    if len(clubs) != 1:
        return None
    club_id = clubs.pop()
    if club_id not in cabinet_senders or sender_addresses[0] not in {s.casefold() for s in cabinet_senders[club_id]}:
        return None
    try:
        sent_at = parsedate_to_datetime(str(mail["Date"])) if mail["Date"] else received_at
    except (TypeError, ValueError):
        sent_at = received_at
    if sent_at.tzinfo is None:
        sent_at = received_at
    body = mail.get_body(preferencelist=("plain",))
    text = str(body.get_content()) if body is not None else ""
    attachments = [name for part in mail.iter_attachments() if (name := part.get_filename()) is not None]
    content = "\n".join(
        [
            f"Forwarded by: {sender_addresses[0]}",
            f"Date: {sent_at.isoformat()}",
            f"Subject: {mail['Subject'] or ''}",
            f"Body: {text}",
            f"Attachments (names only): {', '.join(attachments)}",
        ]
    )[:20_000]
    return CaptureRequest(
        club_id=club_id,
        sources=[
            Untrusted(
                content=content,
                source=SourceRef(kind=SourceKind.EMAIL, source_id=f"gmail/{message_id}", observed_at=sent_at),
            )
        ],
    )


class PendingInbox:
    """Private SQLite queue; a person clicks to process pending requests in Review."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS inbox_capture ("
                "message_id TEXT PRIMARY KEY, club_id TEXT NOT NULL, request_json TEXT NOT NULL, "
                "processed INTEGER NOT NULL DEFAULT 0)"
            )

    def enqueue(self, message_id: str, request: CaptureRequest) -> bool:
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO inbox_capture (message_id, club_id, request_json) VALUES (?, ?, ?)",
                (message_id, request.club_id, request.model_dump_json()),
            )
        return cursor.rowcount == 1

    def pending(self, club_id: str) -> list[tuple[str, CaptureRequest]]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT message_id, request_json FROM inbox_capture "
                "WHERE club_id=? AND processed=0 ORDER BY message_id",
                (club_id,),
            ).fetchall()
        return [(message_id, CaptureRequest.model_validate_json(raw)) for message_id, raw in rows]

    def mark_processed(self, message_id: str, club_id: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE inbox_capture SET processed=1 WHERE message_id=? AND club_id=?",
                (message_id, club_id),
            )
