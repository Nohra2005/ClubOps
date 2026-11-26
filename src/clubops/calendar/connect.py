"""Connecting a club's Google Calendar from inside the app (T-46, D-155).

Google sign-in stays separate from Calendar access (D-116). The president presses Connect, Google asks for
``calendar.events`` and ``calendar.acls``, and the refresh token is kept here encrypted at rest. The browser never
sees the token, the calendar id or the key. Nothing here sends an event; the sync queue does that.

Three small private tables live in ``calendar-auth.db`` next to the queue (never in the repository):
``connection`` (one encrypted token per club), ``oauth_state`` (one-use proofs that a callback belongs to the
person who pressed Connect) and ``sharing_pending`` (reader grants and revokes that Google has not applied yet)."""

from __future__ import annotations

import base64
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SCOPES = (
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.acls",
)
STATE_MINUTES = 10  # how long a Connect click stays valid
AUTH_FILE = "calendar-auth.db"


def token_key(session_secret: str, explicit: str | None = None) -> bytes:
    """The key that locks stored tokens: ``CLUBOPS_CALENDAR_TOKEN_KEY`` if the host sets one, else one derived from
    the session secret (changing the session secret then means reconnecting, nothing else)."""
    if explicit:
        return explicit.encode()
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"clubops-calendar-token").derive(
        session_secret.encode()
    )
    return base64.urlsafe_b64encode(derived)


def authorization_url(client_id: str, redirect_uri: str, state: str, scopes: tuple[str, ...] = SCOPES) -> str:
    """Where the president's browser goes. Offline access and a forced consent screen make Google return a
    refresh token every time; ``include_granted_scopes`` is off so the token holds only these two scopes."""
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "false",
            "state": state,
        }
    )
    return f"{AUTH_URL}?{query}"


def scopes_ok(granted: str) -> bool:
    """Both scopes must be granted: the person can untick one on Google's screen."""
    return set(SCOPES) <= set(granted.split())


class ConnectionVault:
    def __init__(self, data_dir: Path, key: bytes) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / AUTH_FILE
        self._fernet = Fernet(key)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS connection (club_id TEXT PRIMARY KEY, token BLOB NOT NULL, "
                "connected_by TEXT NOT NULL, connected_at TEXT NOT NULL, needs_reconnect INTEGER NOT NULL DEFAULT 0)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS oauth_state (state TEXT PRIMARY KEY, club_id TEXT NOT NULL, "
                "member_id TEXT NOT NULL, expires TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS sharing_pending (club_id TEXT NOT NULL, email TEXT NOT NULL, "
                "action TEXT NOT NULL, last_error TEXT, PRIMARY KEY (club_id, email))"
            )

    # ---------------------------------------------------------- one-use state

    def begin(self, club_id: str, member_id: str, now: datetime) -> str:
        state = secrets.token_urlsafe(32)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM oauth_state WHERE expires < ?", (now.isoformat(),))
            db.execute(
                "INSERT INTO oauth_state VALUES (?, ?, ?, ?)",
                (state, club_id, member_id, (now + timedelta(minutes=STATE_MINUTES)).isoformat()),
            )
        return state

    def consume(self, state: str, club_id: str, member_id: str, now: datetime) -> bool:
        """True once, only for the person and club that started it and only before it expires."""
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute("SELECT club_id, member_id, expires FROM oauth_state WHERE state = ?", (state,)).fetchone()
            db.execute("DELETE FROM oauth_state WHERE state = ?", (state,))
        return bool(row) and row[0] == club_id and row[1] == member_id and now.isoformat() <= str(row[2])

    # ---------------------------------------------------------------- token

    def save(self, club_id: str, refresh_token: str, member_id: str, now: datetime) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT INTO connection VALUES (?, ?, ?, ?, 0) ON CONFLICT (club_id) DO UPDATE SET "
                "token=excluded.token, connected_by=excluded.connected_by, connected_at=excluded.connected_at, "
                "needs_reconnect=0",
                (club_id, self._fernet.encrypt(refresh_token.encode()), member_id, now.isoformat()),
            )

    def load(self, club_id: str) -> str | None:
        """The saved refresh token, or ``None`` when there is none or it can no longer be read."""
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT token FROM connection WHERE club_id = ?", (club_id,)).fetchone()
        if row is None:
            return None
        try:
            return self._fernet.decrypt(bytes(row[0])).decode()
        except InvalidToken:
            self.mark_reconnect(club_id)  # the key changed: the person must connect again
            return None

    def has(self, club_id: str) -> bool:
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT 1 FROM connection WHERE club_id = ?", (club_id,)).fetchone() is not None

    def needs_reconnect(self, club_id: str) -> bool:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT needs_reconnect FROM connection WHERE club_id = ?", (club_id,)).fetchone()
        return bool(row and row[0])

    def mark_reconnect(self, club_id: str) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE connection SET needs_reconnect = 1 WHERE club_id = ?", (club_id,))

    def delete(self, club_id: str) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM connection WHERE club_id = ?", (club_id,))

    # -------------------------------------------------------------- sharing

    def want_share(self, club_id: str, email: str, action: str) -> None:
        """Remember the latest wish for one address: a later revoke replaces an earlier grant, and the reverse."""
        assert action in {"grant", "revoke"}  # noqa: S101 (a programming error, never user input)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT INTO sharing_pending VALUES (?, ?, ?, NULL) ON CONFLICT (club_id, email) DO UPDATE SET "
                "action=excluded.action, last_error=NULL",
                (club_id, email.strip().lower(), action),
            )

    def shares(self, club_id: str) -> list[tuple[str, str]]:
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute(
                "SELECT email, action FROM sharing_pending WHERE club_id = ? ORDER BY email", (club_id,)
            ).fetchall()
        return [(str(r[0]), str(r[1])) for r in rows]

    def share_done(self, club_id: str, email: str, action: str) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "DELETE FROM sharing_pending WHERE club_id = ? AND email = ? AND action = ?", (club_id, email, action)
            )

    def share_failed(self, club_id: str, email: str, problem: str) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "UPDATE sharing_pending SET last_error = ? WHERE club_id = ? AND email = ?", (problem, club_id, email)
            )

    def share_errors(self, club_id: str) -> list[str]:
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute(
                "SELECT last_error FROM sharing_pending WHERE club_id = ? AND last_error IS NOT NULL", (club_id,)
            ).fetchall()
        return [str(r[0]) for r in rows]
