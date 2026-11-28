"""Who is calling the API (T-22): signed session cookies, the member list, and sign-in.

- A session is a cookie holding (member_id, club_id, expiry), signed with HMAC-SHA256. No server session table.
- Members (name, AUB e-mail, role) live in the shared ``general.db`` so sign-in can find a person's club.
- Sign-in is Google (D-56) with any Google account (D-68): the browser sends Google's ID token; we check it
  with Google, then match the e-mail to a member. The president vouches for each e-mail on the list.
  A local "dev" sign-in exists only when CLUBOPS_DEV_LOGIN=1 (tests and local runs).
- Every request that changes something must carry ``X-Requested-With: ClubOps`` (a simple CSRF guard on
  top of SameSite cookies).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from clubops.contracts.common import CABINET_ROLES, Actor, Role

SESSION_COOKIE = "clubops_session"
SESSION_SECONDS = 7 * 24 * 3600
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "ClubOps"


@dataclass(frozen=True)
class Member:
    member_id: str
    club_id: str
    name: str
    email: str
    role: Role  # the task-ownership label (frozen ``Role`` enum); permissions come from ``role_key`` (J-25)
    role_key: str = ""  # the club role the member holds (``clubops.api.roles``); "" means the legacy default

    def __post_init__(self) -> None:
        if not self.role_key:
            object.__setattr__(self, "role_key", legacy_key(self.role))

    def actor(self) -> Actor:
        return Actor(member_id=self.member_id, club_id=self.club_id, roles=frozenset({self.role}), verified=True)

    @property
    def is_cabinet(self) -> bool:
        return self.role in CABINET_ROLES

    def view(self) -> dict[str, str]:
        return {
            "member_id": self.member_id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "role_key": self.role_key,
        }


# Before J-25 a member's only role was the enum value; these are the club-role keys those values became.
_LEGACY_KEYS = {Role.COMMUNICATIONS: "social_media"}


def legacy_key(role: Role) -> str:
    """The club-role key an old enum-only member holds: the same word, except communications -> social_media."""
    return _LEGACY_KEYS.get(role, role.value)


# ---------------------------------------------------------------- sessions


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_session(secret: str, member_id: str, club_id: str, now: float | None = None) -> str:
    payload = _b64(
        json.dumps({"m": member_id, "c": club_id, "e": int((now or time.time()) + SESSION_SECONDS)}).encode()
    )
    mac = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{mac}"


def read_session(secret: str, token: str | None, now: float | None = None) -> tuple[str, str] | None:
    """(member_id, club_id) if the cookie is ours and not expired."""
    if not token or token.count(".") != 1:
        return None
    payload, mac = token.split(".")
    good = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(mac, good):
        return None
    try:
        data = json.loads(_unb64(payload))
    except ValueError:
        return None
    if int(data.get("e", 0)) < (now or time.time()):
        return None
    return str(data["m"]), str(data["c"])


# ----------------------------------------------------------------- members

EMAIL_PATTERN = _EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")


class MemberStore:
    """The cabinet list, shared by every request. One SQLite connection serves all request threads, so every
    use of it (including reading the rows) holds a lock: unsynchronized use breaks the connection (issue #45)."""

    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(data_dir / "general.db"), check_same_thread=False)
        with self._lock, self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS members (member_id TEXT PRIMARY KEY, club_id TEXT NOT NULL, "
                "name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, role TEXT NOT NULL, role_key TEXT)"
            )
            # J-25, additive and idempotent: an older file has no role_key column. Add it and fill it from the
            # enum role, never dropping or rewriting the role column that other readers still use.
            columns = {str(row[1]) for row in self._db.execute("PRAGMA table_info(members)")}
            if "role_key" not in columns:
                self._db.execute("ALTER TABLE members ADD COLUMN role_key TEXT")
            for old, key in _LEGACY_KEYS.items():
                self._db.execute(
                    "UPDATE members SET role_key = ? WHERE (role_key IS NULL OR role_key = '') AND role = ?",
                    (key, old.value),
                )
            self._db.execute("UPDATE members SET role_key = role WHERE role_key IS NULL OR role_key = ''")

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _one(self, sql: str, params: tuple[str, ...]) -> Any:
        with self._lock:
            return self._db.execute(sql, params).fetchone()

    def _all(self, sql: str, params: tuple[str, ...]) -> list[Any]:
        with self._lock:
            return self._db.execute(sql, params).fetchall()

    @staticmethod
    def _row(row: tuple[str, str, str, str, str, str | None] | None) -> Member | None:
        return None if row is None else Member(row[0], row[1], row[2], row[3], Role(row[4]), row[5] or "")

    _COLUMNS = "SELECT member_id, club_id, name, email, role, role_key FROM members"

    def get(self, member_id: str) -> Member | None:
        return self._row(self._one(f"{self._COLUMNS} WHERE member_id = ?", (member_id,)))

    def by_email(self, email: str) -> Member | None:
        return self._row(self._one(f"{self._COLUMNS} WHERE email = ?", (email.strip().lower(),)))

    def of_club(self, club_id: str) -> list[Member]:
        rows = self._all(f"{self._COLUMNS} WHERE club_id = ? ORDER BY name", (club_id,))
        found = []
        for row in rows:
            try:
                member = self._row(row)
            except ValueError:  # a stored label outside the Role enum: skip that row, keep the club working (F-408)
                continue
            if member is not None:
                found.append(member)
        return found

    def holding(self, club_id: str, role_key: str) -> list[Member]:
        """The club's members who hold one club role (J-25)."""
        return [m for m in self.of_club(club_id) if m.role_key == role_key]

    def everyone(self) -> list[Member]:
        """Every member of every club, for the start-up role migration (J-25)."""
        rows = self._all(f"{self._COLUMNS} ORDER BY club_id, name", ())
        return [m for m in (self._row(r) for r in rows) if m is not None]

    def club_ids(self) -> set[str]:
        return {str(r[0]) for r in self._all("SELECT DISTINCT club_id FROM members", ())}

    def relabel(self, club_id: str, role_key: str, role: Role) -> int:
        """Give everyone holding a club role its new task label. Returns how many rows changed (J-25)."""
        with self._lock, self._db:
            cur = self._db.execute(
                "UPDATE members SET role = ? WHERE club_id = ? AND role_key = ?", (role.value, club_id, role_key)
            )
            return cur.rowcount

    INSERT = "INSERT INTO members (member_id, club_id, name, email, role, role_key) VALUES (?, ?, ?, ?, ?, ?)"

    @property
    def lock(self) -> threading.RLock:
        """Held while a caller writes a member row on its own connection, so no two writers pick the same id."""
        return self._lock

    def new_row(
        self, club_id: str, name: str, email: str, role: Role, role_key: str | None = None
    ) -> tuple[str, str, str, str, str, str]:
        """A checked members row with a free id, not yet written. Call with ``lock`` held until it is written."""
        email = email.strip().lower()
        if not _EMAIL.match(email):
            raise ValueError("this is not an e-mail address")
        if role is Role.MEMBER:
            raise ValueError("only cabinet members and the adviser have accounts")
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "member"
        member_id, n = f"m-{slug}", 1
        while self.get(member_id) is not None:
            n += 1
            member_id = f"m-{slug}-{n}"
        return (member_id, club_id, name.strip(), email, role.value, role_key or legacy_key(role))

    def add(self, club_id: str, name: str, email: str, role: Role, role_key: str | None = None) -> Member:
        """``role`` is the task label; ``role_key`` the club role (J-25), by default the legacy key of ``role``."""
        with self._lock:  # pick a free id and insert it as one step, so two requests can't take the same id
            row = self.new_row(club_id, name, email, role, role_key)
            with self._db:
                self._db.execute(self.INSERT, row)
            member = self.get(row[0])
        assert member is not None  # noqa: S101 (just written)
        return member

    def remove(self, club_id: str, member_id: str) -> bool:
        with self._lock, self._db:
            cur = self._db.execute("DELETE FROM members WHERE member_id = ? AND club_id = ?", (member_id, club_id))
            return cur.rowcount == 1


# ------------------------------------------------------------------ google

GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"


def google_email(id_token: str, client_id: str, transport: httpx.BaseTransport | None = None) -> str | None:
    """The verified e-mail inside a Google ID token meant for us, or None."""
    try:
        with httpx.Client(transport=transport, timeout=10) as http:
            response = http.get(GOOGLE_TOKENINFO, params={"id_token": id_token})
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    info = response.json()
    if info.get("aud") != client_id or str(info.get("email_verified")).lower() != "true":
        return None
    email = info.get("email")
    return str(email).lower() if email else None
