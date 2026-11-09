"""C-21: resumable club setup. Integration supplies authenticated, public callbacks.

Answers are untrusted learning inputs, never profile edits or approved knowledge.
An outbox preserves extracted proposals across queue failures; submit must be
idempotent by proposal_id. No raw answers or model calls live in progress rows.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from clubops.contracts.common import Actor, ClubId, Role, SourceKind, SourceRef, Untrusted
from clubops.contracts.knowhow import CaptureRequest, CaptureResult, ItemStatus, KnowHowProposal, Scope

QUESTIONS = (
    "What is your club or society's official name?",
    "Are you a club or a faculty society? If a society, which faculty?",
    "Which department or office advises your club? Keep personal contact details in Cabinet, not here.",
    "Which cabinet roles handle which responsibilities? Use roles, not people's names or contact details.",
    "What are your signature events and activities?",
    "Which venues do you usually use, and for what?",
    "Which organizations sponsor or partner with your club? Omit personal contact details.",
    "What recurring dates or seasonal activities should the next cabinet know about?",
    "Which communication channels do you use? Do not paste private links, credentials or contact details.",
    "What practical lesson should the next cabinet carry forward?",
)
Capture = Callable[[CaptureRequest], CaptureResult]
Submit = Callable[[KnowHowProposal], None]


class SetupStep(BaseModel):
    model_config = ConfigDict(frozen=True)
    question: str
    index: int
    total: int
    done: bool
    rules_count: int


class SetupAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    answer: str | None = Field(default=None, min_length=1, max_length=2000)


class SetupConflict(Exception):
    """Progress is busy or the answer does not match an outstanding retry."""


class SetupService:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "setup"

    def _path(self, club_id: str) -> Path:
        # Authenticated ids still cross a filesystem boundary: validate, do not sanitize.
        slug = TypeAdapter(ClubId).validate_python(club_id)
        return self.root / f"{slug}.sqlite3"

    def complete(self, club_id: str) -> bool:
        path = self._path(club_id)
        if not path.exists():
            return False
        with closing(sqlite3.connect(path, timeout=1)) as connection:
            try:
                row = connection.execute("SELECT position FROM progress WHERE singleton = 1").fetchone()
            except sqlite3.OperationalError as error:
                if "no such table: progress" in str(error):
                    return False  # a concurrent first request has not initialized the file yet
                raise
        return row is not None and int(row[0]) >= len(QUESTIONS)

    @staticmethod
    def _view(position: int, rules_count: int) -> SetupStep:
        done = position >= len(QUESTIONS)
        return SetupStep(
            question="Your club is ready to start." if done else QUESTIONS[position],
            index=min(position + 1, len(QUESTIONS)),
            total=len(QUESTIONS),
            done=done,
            rules_count=max(0, rules_count),
        )

    def next(
        self,
        actor: Actor,
        answer: str | None,
        *,
        now: datetime,
        rules_count: int,
        capture: Capture,
        submit: Submit,
    ) -> SetupStep:
        if not actor.verified or Role.PRESIDENT not in actor.roles:
            raise PermissionError("Only the club president can complete setup.")
        answer = SetupAnswer(answer=answer).answer
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("setup needs an aware clock")
        path = self._path(actor.club_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=0.2, isolation_level=None)
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS progress (singleton INTEGER PRIMARY KEY CHECK(singleton = 1), "
                "position INTEGER NOT NULL, digest TEXT, pending TEXT)"
            )
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO progress(singleton, position) VALUES (1, 0)")
            position, digest, pending = connection.execute(
                "SELECT position, digest, pending FROM progress WHERE singleton = 1"
            ).fetchone()
            position = int(position)
            if pending is not None:
                if answer is not None and self._digest(actor.club_id, position, answer) != digest:
                    raise SetupConflict("Resume setup to finish the previous answer before answering another question.")
                result = CaptureResult.model_validate_json(pending)
            elif position >= len(QUESTIONS) and answer is not None:
                raise SetupConflict("Setup is already complete. Resume to check it, or add new facts in Chat.")
            elif answer is None:
                connection.commit()
                return self._view(position, rules_count)
            elif answer == "[skip]":
                result = CaptureResult(proposals=[], sources_seen=0, sources_skipped=0)
            else:
                source = Untrusted(
                    content=f"Club setup question: {QUESTIONS[position]}\nAnswer: {answer}",
                    source=SourceRef(
                        kind=SourceKind.INTERVIEW,
                        source_id=f"setup-{actor.club_id}-{position + 1}",
                        locator=f"Club setup question {position + 1}",
                        observed_at=now,
                    ),
                )
                result = capture(CaptureRequest(club_id=actor.club_id, sources=[source]))
            self._validate(result, actor.club_id)
            if pending is None:
                connection.execute(
                    "UPDATE progress SET digest = ?, pending = ? WHERE singleton = 1",
                    (self._digest(actor.club_id, position, answer or ""), result.model_dump_json()),
                )
                # Extraction has no writes. Durably preserve its exact output before queueing.
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                current = connection.execute("SELECT position FROM progress WHERE singleton = 1").fetchone()
                if int(current[0]) != position:
                    connection.commit()
                    return self._view(int(current[0]), rules_count)
            for proposal in result.proposals:
                submit(proposal)
            connection.execute(
                "UPDATE progress SET position = ?, digest = NULL, pending = NULL WHERE singleton = 1",
                (position + 1,),
            )
            connection.commit()
            return self._view(position + 1, rules_count)
        except sqlite3.OperationalError as error:
            if "locked" in str(error):
                raise SetupConflict("Setup is busy. Wait for the other request, then resume setup.") from None
            raise
        finally:
            connection.close()

    @staticmethod
    def _digest(club_id: str, position: int, answer: str) -> str:
        return hashlib.sha256(f"{club_id}/{position}/{answer}".encode()).hexdigest()

    @staticmethod
    def _validate(result: CaptureResult, club_id: str) -> None:
        if result.sources_failed:
            raise ValueError("Setup could not read the answer. Retry without advancing the question.")
        if any(
            proposal.candidate.scope is not Scope.CLUB
            or proposal.candidate.club_id != club_id
            or proposal.candidate.status is not ItemStatus.PROPOSED
            or proposal.candidate.verified_by is not None
            or proposal.candidate.verified_at is not None
            for proposal in result.proposals
        ):
            raise ValueError("setup proposals must be unapproved facts for this club")


def router(
    service: SetupService,
    *,
    actor_dependency: Callable[..., Actor],
    capture: Capture,
    submit: Submit,
    rules_count: Callable[[str, date], int],
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> APIRouter:
    """App owner wires its authenticated Actor and public learner/store callbacks.

    capture must use Learner.capture (not .learn), bounded to 8 steps/$0.05;
    submit must queue by proposal_id idempotently, never verify. Rules are counted
    from current, approved AUB-scope knowledge, never copied into each club.
    """
    routes = APIRouter()
    authenticated = Depends(actor_dependency)

    @routes.post("/api/setup/next")
    def next_setup(
        body: SetupAnswer,
        request: Request,
        actor: Actor = authenticated,
    ) -> SetupStep:
        if request.headers.get("X-Requested-With") != "ClubOps":
            raise HTTPException(403, "Missing ClubOps request header.")
        if not actor.verified or Role.PRESIDENT not in actor.roles:
            raise HTTPException(403, "Only the club president can complete setup.")
        now = clock()
        try:
            return service.next(
                actor,
                body.answer,
                now=now,
                rules_count=rules_count(actor.club_id, now.astimezone(ZoneInfo("Asia/Beirut")).date()),
                capture=capture,
                submit=submit,
            )
        except SetupConflict as error:
            raise HTTPException(409, str(error)) from None
        except Exception:
            raise HTTPException(503, "Setup could not finish. Keep your answer and resume to retry safely.") from None

    return routes
