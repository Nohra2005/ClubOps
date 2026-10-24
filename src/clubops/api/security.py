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
import time
from dataclasses import dataclass
from pathlib import Path

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
    role: Role

    def actor(self) -> Actor:
        return Actor(member_id=self.member_id, club_id=self.club_id, roles=frozenset({self.role}), verified=True)

    @property
    def is_cabinet(self) -> bool:
        return self.role in CABINET_ROLES

    def view(self) -> dict[str, str]:
        return {"member_id": self.member_id, "name": self.name, "email": self.email, "role": self.role.value}


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

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")


class MemberStore:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(data_dir / "general.db"), check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS members (member_id TEXT PRIMARY KEY, club_id TEXT NOT NULL, "
            "name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, role TEXT NOT NULL)"
        )

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _row(row: tuple[str, str, str, str, str] | None) -> Member | None:
        return None if row is None else Member(row[0], row[1], row[2], row[3], Role(row[4]))

    def get(self, member_id: str) -> Member | None:
        return self._row(self._db.execute("SELECT * FROM members WHERE member_id = ?", (member_id,)).fetchone())

    def by_email(self, email: str) -> Member | None:
        row = self._db.execute("SELECT * FROM members WHERE email = ?", (email.strip().lower(),)).fetchone()
        return self._row(row)

    def of_club(self, club_id: str) -> list[Member]:
        rows = self._db.execute("SELECT * FROM members WHERE club_id = ? ORDER BY name", (club_id,)).fetchall()
        return [m for m in (self._row(r) for r in rows) if m is not None]

    def add(self, club_id: str, name: str, email: str, role: Role) -> Member:
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
        with self._db:
            self._db.execute(
                "INSERT INTO members VALUES (?, ?, ?, ?, ?)", (member_id, club_id, name.strip(), email, role.value)
            )
        member = self.get(member_id)
        assert member is not None  # noqa: S101 (just written)
        return member

    def remove(self, club_id: str, member_id: str) -> bool:
        with self._db:
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
