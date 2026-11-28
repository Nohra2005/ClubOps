"""Per-club roles with feature permissions, and operator-approved club sign-up (J-25, D-201).

The frozen ``Role`` enum stays what it was: the *task-ownership label* the planner, calendar and learning use.
What a signed-in person may *do* in the app is a separate, API-layer idea kept here:

- Every club has five base roles (president, vice president, treasurer, secretary, social media). They are
  created automatically and the president can neither edit nor delete them.
- The president may add custom roles: a display name, any subset of the grantable features, and a task label
  (a cabinet ``Role`` other than president). A custom role can be deleted only when nobody holds it.
- Managing members and roles, connecting or sharing the calendar and restoring expired knowledge are never a
  feature: they stay with the president. Reading (events, calendar, knowledge, review list, handover, usage) is
  open to every signed-in member, the read-only adviser included, and is not a feature either.

Members store a ``role_key``; the members table keeps its enum ``role`` column as the task label. Start-up
migration is additive and idempotent: every club with members gets the base roles, and holders of the old
``events`` and ``sponsorship`` labels get a custom role of that name, so nobody loses their account or calendar.
By the agreed grant table, roles that are not president or vice president (treasurer, social media, secretary and
the migrated Events and Sponsorship roles) no longer approve plans, decide Review cards or edit knowledge, and only
the secretary keeps the inbox; the president can grant these to a custom role.

New clubs come from a sign-up request: a person proves their e-mail with Google, asks for a club, and an operator
of this host approves (the club is created with its base roles and the requester as president) or rejects it.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from clubops.api.security import EMAIL_PATTERN, Member, MemberStore
from clubops.contracts.common import CABINET_ROLES, Role

# ---------------------------------------------------------------- features

PLAN_EVENTS = "plan_events"
APPROVE_PLANS = "approve_plans"
TASKS = "tasks"
DRAFTS = "drafts"
CHAT = "chat"
UPLOAD = "upload"
REVIEW_APPROVE = "review_approve"
KNOWLEDGE_EDIT = "knowledge_edit"
INBOX = "inbox"
CALENDAR_ACCESS = "calendar_access"

FEATURES: tuple[str, ...] = (
    PLAN_EVENTS,
    APPROVE_PLANS,
    TASKS,
    DRAFTS,
    CHAT,
    UPLOAD,
    REVIEW_APPROVE,
    KNOWLEDGE_EDIT,
    INBOX,
    CALENDAR_ACCESS,
)
Feature = Literal[
    "plan_events",
    "approve_plans",
    "tasks",
    "drafts",
    "chat",
    "upload",
    "review_approve",
    "knowledge_edit",
    "inbox",
    "calendar_access",
]

PRESIDENT_KEY = "president"
ADVISER_KEY = "adviser"

_EVERYONE = frozenset({PLAN_EVENTS, TASKS, DRAFTS, CHAT, UPLOAD, CALENDAR_ACCESS})
_LEADS = frozenset(FEATURES)


@dataclass(frozen=True)
class BaseRole:
    key: str
    name: str
    label: Role
    features: frozenset[str]


BASE_ROLES: tuple[BaseRole, ...] = (
    BaseRole(PRESIDENT_KEY, "President", Role.PRESIDENT, _LEADS),
    BaseRole("vice_president", "Vice President", Role.VICE_PRESIDENT, _LEADS),
    BaseRole("treasurer", "Treasurer", Role.TREASURER, _EVERYONE),
    BaseRole("secretary", "Secretary", Role.SECRETARY, _EVERYONE | {INBOX}),
    BaseRole("social_media", "Social Media", Role.COMMUNICATIONS, _EVERYONE),
)
BASE_KEYS = frozenset(b.key for b in BASE_ROLES)
TREASURER_GRANTS = _EVERYONE  # what the migrated Events and Sponsorship roles start with

# Old enum labels that are not a base role become a custom role of that name for their club (migration).
LEGACY_CUSTOM: dict[Role, str] = {Role.EVENTS: "Events", Role.SPONSORSHIP: "Sponsorship"}

# A custom role's task label: any cabinet label but the president's (only the president role carries that).
TASK_LABELS = frozenset(CABINET_ROLES - {Role.PRESIDENT})
_RESERVED = BASE_KEYS | {ADVISER_KEY, Role.MEMBER.value}


class RoleError(Exception):
    """An expected refusal with the HTTP status the route answers and a plain sentence."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class ClubRole:
    club_id: str
    key: str
    name: str
    task_label: Role
    features: frozenset[str]
    base: bool

    def view(self, holders: int = 0) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "task_label": self.task_label.value,
            "features": [f for f in FEATURES if f in self.features],
            "base": self.base,
            "editable": not self.base,
            "holders": holders,
        }


def _slug(text: str, sep: str) -> str:
    return re.sub(r"[^a-z0-9]+", sep, text.lower()).strip(sep)


def _features(chosen: Iterable[str]) -> frozenset[str]:
    found = frozenset(chosen)
    unknown = found - set(FEATURES)
    if unknown:
        raise RoleError(422, f"Unknown feature: {sorted(unknown)[0]}.")
    return found


def _name(name: str) -> str:
    name = " ".join(name.split())
    if not 2 <= len(name) <= 40:
        raise RoleError(422, "A role name has 2 to 40 characters.")
    return name


def _label(label: Role) -> Role:
    if label not in TASK_LABELS:
        raise RoleError(422, "A custom role's task label is a cabinet role other than president.")
    return label


class ClubRoles:
    """Each club's roles, in ``club_roles`` of the shared ``general.db``. One connection serves every request
    thread, so each use holds a lock (as ``MemberStore`` does, issue #45)."""

    def __init__(self, data_dir: Path, members: MemberStore) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self.members = members
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(data_dir / "general.db"), check_same_thread=False, timeout=10)
        with self._lock, self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS club_roles (club_id TEXT NOT NULL, role_key TEXT NOT NULL, "
                "name TEXT NOT NULL, task_label TEXT NOT NULL, features TEXT NOT NULL, base INTEGER NOT NULL, "
                "PRIMARY KEY (club_id, role_key))"
            )
            # A deleted custom role's key is never handed out again, so a member left on it can't inherit a new
            # role's features (F-407).
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS retired_role_keys (club_id TEXT NOT NULL, role_key TEXT NOT NULL, "
                "PRIMARY KEY (club_id, role_key))"
            )

    @property
    def lock(self) -> threading.RLock:
        """Held by a caller that resolves a role and then adds a member to it, so a delete can't run between."""
        return self._lock

    def _retired(self, club_id: str, key: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM retired_role_keys WHERE club_id = ? AND role_key = ?", (club_id, key)
        ).fetchone()
        return row is not None

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # ------------------------------------------------------------ reading

    @staticmethod
    def _row(club_id: str, row: tuple[str, str, str, str, int]) -> ClubRole:
        key, name, label, features, base = row
        return ClubRole(club_id, key, name, Role(label), frozenset(json.loads(features)), bool(base))

    def get(self, club_id: str, key: str) -> ClubRole | None:
        with self._lock:
            row = self._db.execute(
                "SELECT role_key, name, task_label, features, base FROM club_roles WHERE club_id = ? AND role_key = ?",
                (club_id, key),
            ).fetchone()
        return None if row is None else self._row(club_id, row)

    def of_club(self, club_id: str) -> list[ClubRole]:
        with self._lock:
            rows = self._db.execute(
                "SELECT role_key, name, task_label, features, base FROM club_roles WHERE club_id = ?", (club_id,)
            ).fetchall()
        found = [self._row(club_id, r) for r in rows]
        order = {b.key: n for n, b in enumerate(BASE_ROLES)}
        return sorted(found, key=lambda r: (order.get(r.key, len(order)), r.name.lower()))

    def club_ids(self) -> set[str]:
        with self._lock:
            return {str(r[0]) for r in self._db.execute("SELECT DISTINCT club_id FROM club_roles")}

    def role_of(self, member: Member) -> ClubRole | None:
        """The member's club role. A member added outside the app (a script, an older file) whose role row does
        not exist yet gets it from the migration here, so permissions never depend on a restart."""
        if member.role is Role.ADVISER or member.role_key == ADVISER_KEY:
            return None
        found = self.get(member.club_id, member.role_key)
        if found is None:
            self.ensure_club(member.club_id)
            found = self.get(member.club_id, member.role_key)
        return found

    def features_for(self, member: Member) -> frozenset[str]:
        """What the member may do. The adviser, and anyone whose label is not a cabinet one, gets nothing."""
        if member.role not in CABINET_ROLES:
            return frozenset()
        found = self.role_of(member)
        return found.features if found is not None else frozenset()

    def name_of(self, member: Member) -> str:
        if member.role is Role.ADVISER:
            return "Adviser"
        found = self.role_of(member)
        return found.name if found is not None else member.role_key.replace("_", " ").title()

    # ---------------------------------------------------------- migration

    def _insert(self, role: ClubRole) -> None:
        self._db.execute(
            "INSERT OR IGNORE INTO club_roles VALUES (?, ?, ?, ?, ?, ?)",
            (
                role.club_id,
                role.key,
                role.name,
                role.task_label.value,
                json.dumps(sorted(role.features)),
                int(role.base),
            ),
        )

    @staticmethod
    def base_rows(club_id: str) -> list[tuple[str, str, str, str, str, int]]:
        """The five base roles as ``club_roles`` rows, for a caller writing them inside its own transaction."""
        return [(club_id, b.key, b.name, b.label.value, json.dumps(sorted(b.features)), 1) for b in BASE_ROLES]

    def seed(self, club_id: str) -> None:
        """The five base roles, if missing. Never overwrites a row that exists."""
        with self._lock, self._db:
            for b in BASE_ROLES:
                self._insert(ClubRole(club_id, b.key, b.name, b.label, b.features, base=True))

    def ensure_club(self, club_id: str) -> None:
        """Base roles plus a custom role for every old label a member of this club still holds."""
        self.seed(club_id)
        held = {m.role_key: m.role for m in self.members.of_club(club_id)}
        with self._lock, self._db:
            for key, label in held.items():
                if label in LEGACY_CUSTOM and key == label.value:
                    self._insert(ClubRole(club_id, key, LEGACY_CUSTOM[label], label, TREASURER_GRANTS, base=False))

    def migrate(self) -> None:
        """Start-up, idempotent: every club that has members gets its roles. Adds rows only."""
        for club_id in sorted(self.members.club_ids()):
            self.ensure_club(club_id)

    def resolve(self, club_id: str, key: str) -> ClubRole:
        """The role a new member will hold. An old label the club does not have yet (``events``) is created as
        the migration would, so the older Settings screen keeps working."""
        found = self.get(club_id, key)
        if found is None:
            legacy = next((label for label in LEGACY_CUSTOM if label.value == key), None)
            if legacy is not None:
                with self._lock, self._db:
                    self._insert(ClubRole(club_id, key, LEGACY_CUSTOM[legacy], legacy, TREASURER_GRANTS, base=False))
                found = self.get(club_id, key)
        if found is None:
            raise RoleError(404, "No such role in your club.")
        return found

    # --------------------------------------------------------------- CRUD

    def create(self, club_id: str, name: str, features: Iterable[str], task_label: Role = Role.EVENTS) -> ClubRole:
        name, chosen, label = _name(name), _features(features), _label(task_label)
        stem = _slug(name, "_")[:32] or "role"
        if stem in _RESERVED:
            stem = f"{stem}_custom"
        with self._lock:
            if any(r.name.casefold() == name.casefold() for r in self.of_club(club_id)):
                raise RoleError(409, "Your club already has a role with this name.")
            key, n = stem, 1
            while self.get(club_id, key) is not None or self._retired(club_id, key):
                n += 1
                key = f"{stem}_{n}"
            role = ClubRole(club_id, key, name, label, chosen, base=False)
            with self._db:
                self._insert(role)
        return role

    def _custom(self, club_id: str, key: str) -> ClubRole:
        found = self.get(club_id, key)
        if found is None:
            raise RoleError(404, "No such role in your club.")
        if found.base:
            raise RoleError(403, "Base roles can't be changed or deleted.")
        return found

    def update(
        self,
        club_id: str,
        key: str,
        *,
        name: str | None = None,
        features: Iterable[str] | None = None,
        task_label: Role | None = None,
    ) -> tuple[ClubRole, ClubRole]:
        """(before, after). The caller acts on what changed (calendar access, the members' task label)."""
        with self._lock:
            before = self._custom(club_id, key)
            new_name = _name(name) if name is not None else before.name
            if new_name.casefold() != before.name.casefold() and any(
                r.name.casefold() == new_name.casefold() for r in self.of_club(club_id)
            ):
                raise RoleError(409, "Your club already has a role with this name.")
            after = ClubRole(
                club_id,
                key,
                new_name,
                _label(task_label) if task_label is not None else before.task_label,
                _features(features) if features is not None else before.features,
                base=False,
            )
            with self._db:
                self._db.execute(
                    "UPDATE club_roles SET name = ?, task_label = ?, features = ? WHERE club_id = ? AND role_key = ?",
                    (after.name, after.task_label.value, json.dumps(sorted(after.features)), club_id, key),
                )
        return before, after

    def delete(self, club_id: str, key: str) -> None:
        with self._lock:
            self._custom(club_id, key)
            if self.members.holding(club_id, key):
                raise RoleError(409, "Someone still holds this role. Give them another role first.")
            with self._db:
                self._db.execute("DELETE FROM club_roles WHERE club_id = ? AND role_key = ?", (club_id, key))
                self._db.execute("INSERT OR IGNORE INTO retired_role_keys VALUES (?, ?)", (club_id, key))


# ------------------------------------------------------------ club sign-up


@dataclass(frozen=True)
class ClubRequest:
    request_id: str
    email: str
    name: str
    club_name: str
    club_id: str
    created_at: str
    status: str  # pending, approved, rejected
    decided_at: str | None = None
    decided_by: str | None = None

    def view(self) -> dict[str, Any]:
        return {
            "id": self.request_id,
            "email": self.email,
            "name": self.name,
            "club_name": self.club_name,
            "club_id": self.club_id,
            "created_at": self.created_at,
            "status": self.status,
            "decided_at": self.decided_at,
        }


class ClubRequests:
    """Requests to start a club, waiting for an operator. Kept in ``club_requests`` of ``general.db``."""

    _COLUMNS = "request_id, email, name, club_name, club_id, created_at, status, decided_at, decided_by"

    def __init__(self, data_dir: Path, members: MemberStore, roles: ClubRoles) -> None:
        self.data_dir = data_dir
        self.members = members
        self.roles = roles
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(data_dir / "general.db"), check_same_thread=False, timeout=10)
        with self._lock, self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS club_requests (request_id TEXT PRIMARY KEY, email TEXT NOT NULL, "
                "name TEXT NOT NULL, club_name TEXT NOT NULL, club_id TEXT NOT NULL, created_at TEXT NOT NULL, "
                "status TEXT NOT NULL, decided_at TEXT, decided_by TEXT)"
            )

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _many(self, where: str, params: tuple[str, ...]) -> list[ClubRequest]:
        with self._lock:
            rows = self._db.execute(
                f"SELECT {self._COLUMNS} FROM club_requests WHERE {where} ORDER BY created_at",  # noqa: S608 (fixed text)
                params,
            ).fetchall()
        return [ClubRequest(*row) for row in rows]

    def get(self, request_id: str) -> ClubRequest | None:
        found = self._many("request_id = ?", (request_id,))
        return found[0] if found else None

    def pending(self) -> list[ClubRequest]:
        return self._many("status = 'pending'", ())

    def _taken(self, but: str = "") -> set[str]:
        """Club slugs in use: club files, members, roles, and other open or approved requests."""
        clubs = {p.stem for p in (self.data_dir / "clubs").glob("*.db")}
        held = {r.club_id for r in self._many("status IN ('pending', 'approved') AND request_id != ?", (but,))}
        return clubs | held | self.members.club_ids() | self.roles.club_ids()

    def _free_slug(self, club_name: str, taken: set[str]) -> str:
        stem = _slug(club_name, "-")[:48].strip("-")
        if len(stem) < 2:
            stem = f"club-{stem}".strip("-") if stem else "club"
        slug, n = stem, 1
        while slug in taken:
            n += 1
            slug = f"{stem}-{n}"
        return slug

    def create(self, email: str, name: str, club_name: str, now: datetime) -> ClubRequest:
        email = email.strip().lower()
        name, club_name = " ".join(name.split()), " ".join(club_name.split())
        if not 2 <= len(club_name) <= 80 or not _slug(club_name, "-"):
            raise RoleError(422, "A club name has 2 to 80 characters, with letters or digits.")
        if not 2 <= len(name) <= 120:
            raise RoleError(422, "Your name has 2 to 120 characters.")
        if not EMAIL_PATTERN.match(email):
            raise RoleError(422, "This is not an e-mail address.")
        with self._lock:
            if self.members.by_email(email) is not None:
                raise RoleError(409, "This e-mail is already on a club's cabinet list.")
            if self._many("email = ? AND status = 'pending'", (email,)):
                raise RoleError(409, "You already asked for a club. An operator will answer it.")
            request = ClubRequest(
                request_id=f"req-{uuid.uuid4().hex[:12]}",
                email=email,
                name=name,
                club_name=club_name,
                club_id=self._free_slug(club_name, self._taken()),
                created_at=now.isoformat(),
                status="pending",
            )
            with self._db:
                self._db.execute(
                    f"INSERT INTO club_requests ({self._COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",  # noqa: S608
                    (
                        request.request_id,
                        request.email,
                        request.name,
                        request.club_name,
                        request.club_id,
                        request.created_at,
                        request.status,
                        None,
                        None,
                    ),
                )
        return request

    def _waiting(self, request_id: str) -> ClubRequest:
        found = self.get(request_id)
        if found is None:
            raise RoleError(404, "No such club request.")
        if found.status != "pending":
            raise RoleError(409, f"This request was already {found.status}.")
        return found

    def _decide(self, request: ClubRequest, status: str, club_id: str, operator: Member, now: datetime) -> None:
        """Inside the caller's transaction: never commits on its own."""
        self._db.execute(
            "UPDATE club_requests SET status = ?, club_id = ?, decided_at = ?, decided_by = ? WHERE request_id = ?",
            (status, club_id, now.isoformat(), operator.member_id, request.request_id),
        )

    def approve(self, request_id: str, operator: Member, now: datetime) -> tuple[ClubRequest, Member]:
        """Create the club: a free slug, its five base roles, and the requester as president.

        All or nothing (F-409): the roles, the president and the decision are written in one transaction on one
        connection, so a failure at any step leaves no role, no member and a request still pending. Nothing else
        is created here; a club's own files appear on its first use."""
        with self._lock, self.roles.lock, self.members.lock:
            request = self._waiting(request_id)
            if self.members.by_email(request.email) is not None:
                raise RoleError(409, "This e-mail is already on a club's cabinet list.")
            club_id = self._free_slug(request.club_name, self._taken(but=request.request_id))
            try:
                row = self.members.new_row(club_id, request.name, request.email, Role.PRESIDENT, PRESIDENT_KEY)
            except ValueError as err:
                raise RoleError(422, str(err)) from None
            with self._db:  # one transaction: commits only if every statement below succeeds
                self._db.executemany(
                    "INSERT OR IGNORE INTO club_roles VALUES (?, ?, ?, ?, ?, ?)", self.roles.base_rows(club_id)
                )
                self._db.execute(MemberStore.INSERT, row)
                self._decide(request, "approved", club_id, operator, now)
            president = self.members.get(row[0])
        decided = self.get(request_id)
        assert decided is not None and president is not None  # noqa: S101 (just written)
        return decided, president

    def reject(self, request_id: str, operator: Member, now: datetime) -> ClubRequest:
        with self._lock:
            request = self._waiting(request_id)
            with self._db:
                self._decide(request, "rejected", request.club_id, operator, now)
        decided = self.get(request_id)
        assert decided is not None  # noqa: S101 (just written)
        return decided
