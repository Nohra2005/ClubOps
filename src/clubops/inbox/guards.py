"""Free, synthetic-testable checks before a cabinet member pays to read forwarded mail.

The API owner supplies the private OSA allowlist and calls ``mark_read`` only after
Review proposals have been saved. Nothing here calls a model or sends mail.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import time
from collections.abc import Collection
from contextlib import closing
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from pathlib import Path

_TAG = re.compile(r"^clubops\.agent\+([a-z0-9-]+)@gmail\.com$", re.IGNORECASE)
_FORWARD_MARKER = re.compile(
    r"(?im)^\s*(?:-{2,}\s*(?:forwarded message|original message)\s*-{2,}|begin forwarded message:|_{5,})\s*$"
)
_HEADER = re.compile(r"(?im)^(from|subject|date|sent|to|cc|message-id):\s*(.+)$")
_QUOTE = re.compile(r"(?m)^(?:>|On .+ wrote:|From: .+)$")


@dataclass(frozen=True)
class CheckedMail:
    reason: str | None
    content: str = ""
    fingerprint: str = ""
    audience: int | None = None  # how many people the original was sent to (To + Cc); None when unknown (D-126)
    unlisted_sender: bool = False  # the original sender is not on the OSA list; a person chose to read it (D-136)


class InboxLedger:
    """Private verification and read-once records, shared across all clubs."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS sender_checks ("
                "member_id TEXT PRIMARY KEY, club_id TEXT NOT NULL, address TEXT NOT NULL, "
                "salt TEXT NOT NULL, code_hash TEXT NOT NULL, expires_at REAL NOT NULL, "
                "attempts INTEGER NOT NULL DEFAULT 0, verified INTEGER NOT NULL DEFAULT 0)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS read_mail (fingerprint TEXT PRIMARY KEY, "
                "state TEXT NOT NULL, claim_token TEXT, claimed_at REAL)"
            )

    def begin_verification(self, member_id: str, club_id: str, address: str) -> str:
        """Return a short code for the member to send from ``address`` to the club plus-address."""
        normalized = address.strip().casefold()
        if not member_id or not club_id or len(getaddresses([normalized])) != 1 or "@" not in normalized:
            raise ValueError("a member, club and valid sending address are required")
        code = f"{secrets.randbelow(1_000_000):06d}"
        salt = secrets.token_hex(16)
        digest = hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT INTO sender_checks "
                "(member_id, club_id, address, salt, code_hash, expires_at, attempts, verified) "
                "VALUES (?, ?, ?, ?, ?, ?, 0, 0) "
                "ON CONFLICT(member_id) DO UPDATE SET club_id=excluded.club_id, address=excluded.address, "
                "salt=excluded.salt, code_hash=excluded.code_hash, expires_at=excluded.expires_at, "
                "attempts=0, verified=0",
                (member_id, club_id, normalized, salt, digest, time.time() + 600),
            )
        return code

    def verify(self, member_id: str, raw: bytes) -> bool:
        """Accept a code only from the proposed address to that club's plus-address."""
        mail = BytesParser(policy=policy.default).parsebytes(raw)
        senders = [address.casefold() for _, address in getaddresses(mail.get_all("From", []))]
        recipients = [address.casefold() for _, address in getaddresses(mail.get_all("To", []))]
        body = mail.get_body(preferencelist=("plain",))
        text = str(body.get_content()).strip() if body is not None else ""
        if len(senders) != 1 or len(recipients) != 1 or not re.fullmatch(r"\d{6}", text):
            return False
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute(
                "SELECT club_id, address, salt, code_hash, expires_at, attempts FROM sender_checks WHERE member_id=?",
                (member_id,),
            ).fetchone()
            if row is None:
                return False
            club_id, address, salt, digest, expires_at, attempts = row
            if senders[0] != address or recipients[0] != f"clubops.agent+{club_id}@gmail.com":
                return False
            if time.time() >= expires_at or attempts >= 5:
                return False
            if not secrets.compare_digest(hashlib.sha256(f"{salt}:{text}".encode()).hexdigest(), digest):
                db.execute("UPDATE sender_checks SET attempts=attempts+1 WHERE member_id=?", (member_id,))
                return False
            db.execute("UPDATE sender_checks SET verified=1 WHERE member_id=?", (member_id,))
        return True

    def remove_member(self, member_id: str) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM sender_checks WHERE member_id=?", (member_id,))

    def verified_senders(self, club_id: str) -> set[str]:
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute("SELECT address FROM sender_checks WHERE club_id=? AND verified=1", (club_id,)).fetchall()
        return {str(row[0]) for row in rows}

    def was_read(self, fingerprint: str) -> bool:
        with closing(sqlite3.connect(self.path)) as db:
            return (
                db.execute("SELECT 1 FROM read_mail WHERE fingerprint=? AND state='read'", (fingerprint,)).fetchone()
                is not None
            )

    def claim_read(self, fingerprint: str) -> str | None:
        """Reserve one paid read across clubs. A stale claim can be retried after ten minutes."""
        token = secrets.token_urlsafe(16)
        now = time.time()
        with closing(sqlite3.connect(self.path)) as db, db:
            inserted = db.execute(
                "INSERT OR IGNORE INTO read_mail (fingerprint, state, claim_token, claimed_at) "
                "VALUES (?, 'processing', ?, ?)",
                (fingerprint, token, now),
            )
            if inserted.rowcount:
                return token
            renewed = db.execute(
                "UPDATE read_mail SET claim_token=?, claimed_at=? "
                "WHERE fingerprint=? AND state='processing' AND claimed_at<?",
                (token, now, fingerprint, now - 600),
            )
        return token if renewed.rowcount else None

    def mark_read(self, fingerprint: str, token: str) -> bool:
        """Call after Review persistence succeeds; only the current claimant may finish."""
        with closing(sqlite3.connect(self.path)) as db, db:
            changed = db.execute(
                "UPDATE read_mail SET state='read', claim_token=NULL WHERE fingerprint=? "
                "AND state='processing' AND claim_token=?",
                (fingerprint, token),
            )
        return changed.rowcount == 1

    def release_read(self, fingerprint: str, token: str) -> None:
        """Keep a failed capture retryable without releasing another claimant's reservation."""
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "DELETE FROM read_mail WHERE fingerprint=? AND state='processing' AND claim_token=?",
                (fingerprint, token),
            )


_ADDRESS = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")


def count_audience(values: list[str]) -> int | None:
    """How many people the original e-mail went to, from its To and Cc lines. Only the number is kept: the
    addresses belong to other people. Bcc is invisible, and "undisclosed recipients" says nothing, so those
    give None and the caller falls back to the model's own label."""
    addresses = {found.casefold() for value in values for found in _ADDRESS.findall(value)}
    if addresses:
        return len(addresses)
    if any("undisclosed" in value.casefold() for value in values):
        return None
    entries = [entry for value in values for entry in value.split(";") if entry.strip()]
    return len(entries) or None


def check_forward(
    raw: bytes,
    club_id: str,
    authorized_senders: Collection[str],
    osa_senders: Collection[str],
    ledger: InboxLedger,
    *,
    allow_unlisted_sender: bool = False,
) -> CheckedMail:
    """Validate a forward and return clean, still-untrusted text or a skip reason. ``allow_unlisted_sender`` skips
    only the OSA-list check, for an e-mail a cabinet member chose to read anyway; every other check still runs."""
    mail = BytesParser(policy=policy.default).parsebytes(raw)
    senders = [address.casefold() for _, address in getaddresses(mail.get_all("From", []))]
    recipients = [address.casefold() for _, address in getaddresses(mail.get_all("To", []))]
    tags = {match.group(1) for address in recipients if (match := _TAG.fullmatch(address))}
    if tags != {club_id}:
        return CheckedMail("wrong_club_tag")
    if len(senders) != 1 or senders[0] not in {address.casefold() for address in authorized_senders}:
        return CheckedMail("unverified_sender")
    body = mail.get_body(preferencelist=("plain",))
    text = str(body.get_content()) if body is not None else ""
    marker = _FORWARD_MARKER.search(text)
    if marker is None:
        return CheckedMail("missing_forward_headers")
    forwarded = text[marker.end() :]
    headers: dict[str, str] = {}
    audience_lines: list[str] = []
    lines = forwarded.lstrip().splitlines()
    body_start = 0
    for index, line in enumerate(lines):
        if not line.strip():
            body_start = index + 1
            break
        match = _HEADER.match(line)
        if match is None:
            return CheckedMail("malformed_forward_headers")
        name = match.group(1).casefold()
        if name in {"to", "cc"}:
            audience_lines.append(match.group(2))
        elif name != "sent":
            headers[name] = match.group(2).strip()
    origins = [address.casefold() for _, address in getaddresses([headers.get("from", "")])]
    unlisted = len(origins) != 1 or origins[0] not in {address.casefold() for address in osa_senders}
    if unlisted and not (allow_unlisted_sender and len(origins) == 1):
        return CheckedMail("original_sender_not_osa")
    content = "\n".join(lines[body_start:])
    content = _FORWARD_MARKER.split(content, maxsplit=1)[0]
    content = re.split(r"(?m)^\s*--\s*$", content, maxsplit=1)[0]
    content = _QUOTE.split(content, maxsplit=1)[0]
    content = re.sub(r"[ \t]+", " ", content).strip()[:20_000]
    if not content:
        return CheckedMail("empty_forward")
    original_id = headers.get("message-id", "").strip().casefold()
    stable = (
        "\n".join((origins[0], original_id))
        if original_id
        else "\n".join((origins[0], headers.get("subject", ""), content))
    )
    fingerprint = hashlib.sha256(stable.encode()).hexdigest()
    if ledger.was_read(fingerprint):
        return CheckedMail("already_read")
    return CheckedMail(None, content, fingerprint, count_audience(audience_lines), unlisted)
