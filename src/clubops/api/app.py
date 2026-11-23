"""The HTTP API the web app calls (T-22). Paths and field names follow the UI spec's API table.

Run locally:  CLUBOPS_DEV_LOGIN=1 CLUBOPS_COOKIE_SECURE=0 uv run uvicorn clubops.api.app:build --factory --reload

Conventions (agreed for C-13):
- JSON in and out; screens get the view models in ``views.py``; ``/runs/*`` returns the ``AgentRun`` contract.
- Errors are HTTP codes with ``{"detail": "<plain sentence>"}``: 401 not signed in, 403 not allowed,
  404 not found (also another club's data), 409 changed since you loaded it, 422 bad input, 501 not built yet.
- Every POST, PATCH and DELETE needs the header ``X-Requested-With: ClubOps``.
- The club comes from the sign-in, never from the URL; one club can never read another club's file.
"""

from __future__ import annotations

import io
import os
import re
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import httpx
import openpyxl
from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from clubops.agent.planner import ModelDecider, Planner, RunState
from clubops.agent.rules_judge import RuleJudge
from clubops.agent.runs import RunStore
from clubops.api import views
from clubops.api.handover import guide_view
from clubops.api.security import (
    CSRF_HEADER,
    CSRF_VALUE,
    SESSION_COOKIE,
    SESSION_SECONDS,
    Member,
    MemberStore,
    google_email,
    read_session,
    sign_session,
)
from clubops.api.setup import SetupService
from clubops.api.setup import router as setup_router
from clubops.api.store import ApiStore, PlannedEvent
from clubops.calendar.items import event_items, impact_form_item
from clubops.capabilities.runner import CapabilityError
from clubops.config import _read_dotenv, load_settings
from clubops.contracts.agent import AgentRun, PlanEventRequest, RunStatus
from clubops.contracts.common import Actor, ErrorCode, Role, SourceKind, SourceRef, Untrusted
from clubops.contracts.event import Audience, EventSpec, EventStatus, Venue, VenueKind
from clubops.contracts.handover import HandoverRequest
from clubops.contracts.knowhow import (
    CaptureRequest,
    CaptureResult,
    ItemStatus,
    Kind,
    KnowHowItem,
    KnowHowProposal,
    Scope,
    VerifyDecision,
    VerifyRequest,
)
from clubops.inbox.capture import PendingInbox
from clubops.inbox.guards import InboxLedger
from clubops.inbox_intake import InboxNotes
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.directory import Directory
from clubops.knowhow.handover import build_handover
from clubops.knowhow.store import KnowHowStore, rescoped
from clubops.learning.capture import Candidate, Learner, price_list, rows_to_text
from clubops.learning.documents import MAX_PIECES, DocumentError, read_pdf, split_text
from clubops.model.client import ModelClient
from clubops.reports.runs import record_run
from clubops.reports.usage import usage_details

# ------------------------------------------------------------------ settings


@dataclass(frozen=True)
class ApiConfig:
    data_dir: Path
    session_secret: str
    dev_login: bool = False
    google_client_id: str | None = None
    cookie_secure: bool = True


def load_api_config(env: dict[str, str] | None = None, dotenv: Path = Path(".env")) -> ApiConfig:
    values = {**_read_dotenv(dotenv), **(dict(os.environ) if env is None else env)}
    secret = values.get("CLUBOPS_SESSION_SECRET", "")
    dev = values.get("CLUBOPS_DEV_LOGIN") == "1"
    if not secret:
        if not dev:
            raise RuntimeError("CLUBOPS_SESSION_SECRET is required")
        secret = "dev-only-secret"  # noqa: S105 (local dev sign-in only)
    return ApiConfig(
        data_dir=Path(values.get("CLUBOPS_DATA_DIR") or "data/app"),
        session_secret=secret,
        dev_login=dev,
        google_client_id=values.get("CLUBOPS_GOOGLE_CLIENT_ID") or None,
        cookie_secure=values.get("CLUBOPS_COOKIE_SECURE", "1") != "0",
    )


PlannerFactory = Callable[[KnowHowStore, Directory, Callable[[RunState], None]], Planner]


def model_planner(store: KnowHowStore, directory: Directory, on_step: Callable[[RunState], None]) -> Planner:
    settings = load_settings()
    client = ModelClient(settings)
    return Planner(
        ModelDecider(client),
        store,
        directory,
        step_limit=settings.max_steps_per_plan,
        cost_limit_usd=settings.budget_usd_per_packet,
        rules=RuleJudge(client),
        on_step=on_step,
    )


# ------------------------------------------------------------------- inputs


class RestoreBody(BaseModel):
    valid_to: date | None = None


class PlanBody(BaseModel):
    description: str = Field(min_length=3, max_length=4000)


class AnswerBody(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class ApproveBody(BaseModel):
    revision: int = Field(ge=1)


class TaskBody(BaseModel):
    state: Literal["todo", "due_today", "overdue", "done"] | None = None
    owner_role: Role | None = None


class FieldsBody(BaseModel):
    fields: dict[str, str]


class DecisionBody(BaseModel):
    # approve/reject/edit are the plain decisions; the Review screen also sends keep_a, keep_b, merge, both and
    # keep_both for disagreement and merge cards (F-245)
    decision: Literal["approve", "reject", "edit", "keep_a", "keep_b", "merge", "both", "keep_both"]
    edited_text: str | None = Field(default=None, max_length=1500)
    reason: str | None = Field(default=None, max_length=300)
    # None keeps ClubOps' suggestion; True shares the fact with every AUB club, False keeps it in this club (D-91).
    shared: bool | None = None
    opened_at: str | None = None
    decided_at: str | None = None


class EditBody(BaseModel):
    text: str = Field(min_length=3, max_length=1500)


class MemberBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=200)
    role: Role


class RemoveBody(BaseModel):
    member_id: str


class GoogleBody(BaseModel):
    credential: str = Field(min_length=10, max_length=5000)


class DevBody(BaseModel):
    email: str


_HTTP = {
    ErrorCode.NOT_AUTHORIZED: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.STALE_INPUT: 409,
    ErrorCode.INVALID_INPUT: 422,
    ErrorCode.BUDGET_EXCEEDED: 409,
}


MAX_UPLOAD = 2 * 1024 * 1024
MAX_PDF_UPLOAD = 10 * 1024 * 1024

# ---------------------------------------------------------------------- app


# Clubs that were already set up by hand before the setup questions existed, so their president is
# not asked to answer them again (D-112). Remove a club here only if it should go through setup.
SET_UP_BEFORE_C21 = frozenset({"running-club"})


def create_app(  # noqa: PLR0915 (one function per route below; kept together on purpose)
    config: ApiConfig,
    planner_factory: PlannerFactory = model_planner,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    google_transport: httpx.BaseTransport | None = None,
    model_client: Callable[[], ModelClient] = lambda: ModelClient(load_settings()),
    *,
    setup_overrides: Mapping[str, Callable[..., Any]] | None = None,
) -> FastAPI:
    app = FastAPI(title="ClubOps API", docs_url="/api/docs", openapi_url="/api/openapi.json")
    members = MemberStore(config.data_dir)
    setup_service = SetupService(config.data_dir)
    starting: dict[str, str] = {}  # run_id -> club, between "plan" and the agent's first saved step

    def today() -> date:
        return clock().astimezone(views.BEIRUT).date()

    @contextmanager
    def club(club_id: str) -> Iterator[tuple[KnowHowStore, Directory, RunStore, ApiStore]]:
        store = KnowHowStore(open_club_store_backend(config.data_dir, club_id))
        directory, runs, api = (
            Directory(config.data_dir, club_id),
            RunStore(config.data_dir, club_id),
            ApiStore(config.data_dir, club_id),
        )
        try:
            yield store, directory, runs, api
        finally:
            for part in (store, directory, runs, api):
                part.close()

    @app.exception_handler(CapabilityError)
    def _capability_error(_: Request, err: CapabilityError) -> JSONResponse:
        return JSONResponse({"detail": err.message}, status_code=_HTTP.get(err.code, 500))

    @app.middleware("http")
    async def _csrf(request: Request, call_next: Callable[[Request], Any]) -> Response:
        if request.method in {"POST", "PATCH", "DELETE"} and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
            return JSONResponse({"detail": "Missing the ClubOps request header."}, status_code=403)
        return await call_next(request)  # type: ignore[no-any-return]

    # ----------------------------------------------------------- who is it

    def signed_in(request: Request) -> Member:
        found = read_session(config.session_secret, request.cookies.get(SESSION_COOKIE))
        member = members.get(found[0]) if found else None
        if member is None or member.club_id != found[1]:  # type: ignore[index]
            raise HTTPException(401, "Please sign in to continue.")
        return member

    def cabinet(member: Member = Depends(signed_in)) -> Member:  # noqa: B008
        if not member.is_cabinet:
            raise HTTPException(403, "Only cabinet members can do this.")
        return member

    def president(member: Member = Depends(signed_in)) -> Member:  # noqa: B008
        if member.role is not Role.PRESIDENT:
            raise HTTPException(403, "Only the president can change the cabinet list.")
        return member

    def start_session(response: Response, member: Member) -> dict[str, Any]:
        response.set_cookie(
            SESSION_COOKIE,
            sign_session(config.session_secret, member.member_id, member.club_id),
            max_age=SESSION_SECONDS,
            httponly=True,
            secure=config.cookie_secure,
            samesite="lax",
        )
        return me(member)

    @app.post("/api/auth/google")
    def google_sign_in(body: GoogleBody, response: Response) -> dict[str, Any]:
        if not config.google_client_id:
            raise HTTPException(501, "Google sign-in is not set up yet.")
        email = google_email(body.credential, config.google_client_id, google_transport)
        member = members.by_email(email) if email else None
        if member is None:
            raise HTTPException(403, "This account is not on a club's cabinet list. Ask your president to add you.")
        return start_session(response, member)

    @app.post("/api/auth/dev")
    def dev_sign_in(body: DevBody, response: Response) -> dict[str, Any]:
        if not config.dev_login:
            raise HTTPException(404, "Not found.")
        member = members.by_email(body.email)
        if member is None:
            raise HTTPException(403, "No member with this e-mail.")
        return start_session(response, member)

    @app.post("/api/auth/logout", status_code=204)
    def sign_out(response: Response) -> None:
        response.delete_cookie(SESSION_COOKIE)

    # ----------------------------------------------------------------- me

    def event_rows(club_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        with club(club_id) as (store, directory, _, api):
            rules = {r.item_id: r for r in store.current(club_id, today(), kinds=[Kind.RULE])}
            changes = api.task_changes()
            out, all_tasks = [], []
            for e in api.events():
                rows = views.tasks(e, changes, rules, today())
                all_tasks += rows
                out.append(views.summary(directory.event(e.spec.event_id), e, rows))
        out.sort(key=lambda s: s["start"] or "9999")
        return out, all_tasks

    @app.get("/api/me")
    def me(member: Member = Depends(signed_in)) -> dict[str, Any]:  # noqa: B008
        events, tasks = event_rows(member.club_id)
        with club(member.club_id) as (store, _, _, _):
            pending = len(store.pending)
        soon = sum(t["state"] in ("due_today", "overdue") for t in tasks)
        name = member.club_id.replace("-", " ").title()
        return {
            "user": member.view(),
            "role": member.role.value,
            "club": {
                "id": member.club_id,
                "name": name,
                "initials": "".join(w[0] for w in name.split())[:3].upper(),
                "setup_complete": member.club_id in SET_UP_BEFORE_C21 or setup_service.complete(member.club_id),
            },
            "counts": {
                "overdue_events": sum(e["overdue_tasks"] > 0 for e in events),
                "review": pending,
                "reminders": soon,
            },
        }

    # ------------------------------------------------------------- events

    @app.get("/api/events")
    def list_events(member: Member = Depends(signed_in)) -> list[dict[str, Any]]:  # noqa: B008
        return event_rows(member.club_id)[0]

    def event_detail(club_id: str, event_id: str) -> dict[str, Any]:
        with club(club_id) as (store, directory, _, api):
            event = api.event(event_id)
            if event is None or event.spec.club_id != club_id:
                raise HTTPException(404, "No such event.")
            rules = {r.item_id: r for r in store.current(club_id, today(), kinds=[Kind.RULE])}
            rows = views.tasks(event, api.task_changes(), rules, today())
            return views.detail(directory.event(event_id), event, rows, rules)

    @app.get("/api/events/{event_id}")
    def get_event(event_id: str, member: Member = Depends(signed_in)) -> dict[str, Any]:  # noqa: B008
        return event_detail(member.club_id, event_id)

    def run_plan(club_id: str, run_id: str, description: str, spec: EventSpec | None) -> None:
        with club(club_id) as (store, directory, runs, api):

            def save(state: RunState) -> None:
                runs.save(state)
                api.record_usage(state.run.run_id, clock(), state.run.steps_used, state.run.cost_usd)
                record_run(config.data_dir, club_id, state.run, clock())

            planner = planner_factory(store, directory, save)
            words = Untrusted(
                content=description,
                source=SourceRef(kind=SourceKind.USER_INPUT, source_id=f"plan/{run_id}", observed_at=clock()),
            )
            try:
                state = planner.start(PlanEventRequest(club_id=club_id, description=words, today=today()), run_id, spec)
                finish(state, runs, api)
            except CapabilityError:
                pass  # the run's own steps say what failed
            finally:
                starting.pop(run_id, None)

    def finish(state: RunState, runs: RunStore, api: ApiStore) -> None:
        runs.save(state)
        api.record_usage(state.run.run_id, clock(), state.run.steps_used, state.run.cost_usd)
        record_run(config.data_dir, state.run.club_id, state.run, clock())
        if state.run.status is RunStatus.DONE:
            old = api.event(state.spec.event_id)
            api.save_event(
                PlannedEvent(
                    spec=state.spec,
                    plan=state.plan,
                    rules=state.rules,
                    run_id=state.run.run_id,
                    approved_by=old.approved_by if old else None,
                    approved_at=old.approved_at if old else None,
                    approved_revision=old.approved_revision if old else None,
                )
            )

    @app.post("/api/events/plan", status_code=202)
    def plan_event(body: PlanBody, background: BackgroundTasks, member: Member = Depends(cabinet)) -> dict[str, str]:  # noqa: B008
        """Starts the agent after answering; the UI polls GET /api/runs/{run_id}."""
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        starting[run_id] = member.club_id
        background.add_task(run_plan, member.club_id, run_id, body.description, None)
        return {"run_id": run_id}

    @app.post("/api/events/{event_id}/rebuild", status_code=202)
    def rebuild(event_id: str, background: BackgroundTasks, member: Member = Depends(cabinet)) -> dict[str, str]:  # noqa: B008
        with club(member.club_id) as (_, _, _, api):
            event = api.event(event_id)
        if event is None:
            raise HTTPException(404, "No such event.")
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        starting[run_id] = member.club_id
        background.add_task(run_plan, member.club_id, run_id, event.spec.description or "re-plan", event.spec)
        return {"run_id": run_id}

    def load_run(member: Member, run_id: str) -> RunState:
        with club(member.club_id) as (_, _, runs, _):
            state = runs.get(run_id)
        if state is None or state.run.club_id != member.club_id:
            raise HTTPException(404, "No such run.")
        return state

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, member: Member = Depends(signed_in)) -> dict[str, Any]:  # noqa: B008
        """While the agent is still on its first step, the run shows as running with no steps."""
        if starting.get(run_id) == member.club_id:
            with club(member.club_id) as (_, _, runs, _):
                saved = runs.get(run_id)
            if saved is None:
                settings = load_settings()
                return AgentRun(
                    run_id=run_id,
                    club_id=member.club_id,
                    status=RunStatus.RUNNING,
                    steps=[],
                    steps_used=0,
                    step_limit=settings.max_steps_per_plan,
                    cost_usd=Decimal("0"),
                    cost_limit_usd=settings.budget_usd_per_packet,
                ).model_dump(mode="json")
        return load_run(member, run_id).run.model_dump(mode="json")

    def continue_run(member: Member, run_id: str, how: Callable[[Planner, RunState], RunState]) -> dict[str, Any]:
        state = load_run(member, run_id)
        with club(member.club_id) as (store, directory, runs, api):

            def save(s: RunState) -> None:
                runs.save(s)
                api.record_usage(s.run.run_id, clock(), s.run.steps_used, s.run.cost_usd)
                record_run(config.data_dir, member.club_id, s.run, clock())

            planner = planner_factory(store, directory, save)
            new = how(planner, state)
            finish(new, runs, api)
        return new.run.model_dump(mode="json")

    @app.post("/api/runs/{run_id}/answer")
    def answer_run(run_id: str, body: AnswerBody, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        return continue_run(member, run_id, lambda p, s: p.answer(s, body.text))

    @app.post("/api/runs/{run_id}/continue")
    def keep_going(run_id: str, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        return continue_run(member, run_id, lambda p, s: p.keep_going(s))

    @app.patch("/api/events/{event_id}")
    def edit_event(event_id: str, body: FieldsBody, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        with club(member.club_id) as (_, _, _, api):
            event = api.event(event_id)
            if event is None:
                raise HTTPException(404, "No such event.")
            try:
                spec = apply_fields(event.spec, body.fields)
            except ValueError as err:
                raise HTTPException(422, f"Those details don't fit together: {str(err).splitlines()[0]}") from None
            event.spec = spec
            api.save_event(event)
        return event_detail(member.club_id, event_id)

    @app.post("/api/events/{event_id}/approve-plan")
    def approve_plan(event_id: str, body: ApproveBody, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        with club(member.club_id) as (_, directory, _, api):
            event = api.event(event_id)
            if event is None:
                raise HTTPException(404, "No such event.")
            if event.plan_outdated or body.revision != event.spec.revision:
                raise HTTPException(409, "This plan changed. Reload it before approving.")
            spec, plan = event.spec, event.plan
            assert plan is not None  # noqa: S101 (plan_outdated is False)
            if not (spec.title and spec.start and spec.end):
                raise HTTPException(422, "Add the event's title, date and times before approving.")
            items = [*event_items(spec, plan, approved=True), impact_form_item(spec.club_id, event_id, spec.end)]
            api.put_calendar(items)
            event.approved_by, event.approved_at = member.member_id, clock().isoformat()
            event.approved_revision = spec.revision
            api.save_event(event)
            record = directory.event(event_id)
            if record is not None:
                directory.put_event(record.model_copy(update={"status": EventStatus.APPROVED}))
        return event_detail(member.club_id, event_id)

    @app.patch("/api/tasks/{task_id:path}")
    def change_task(task_id: str, body: TaskBody, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        event_id = task_id.split("/", 1)[0]
        detail = event_detail(member.club_id, event_id)
        if not any(t["task_id"] == task_id for t in detail["tasks"]):
            raise HTTPException(404, "No such task.")
        with club(member.club_id) as (_, _, _, api):
            api.change_task(task_id, body.state, body.owner_role.value if body.owner_role else None)
        return next(t for t in event_detail(member.club_id, event_id)["tasks"] if t["task_id"] == task_id)

    # ----------------------------------------------------------- calendar

    @app.get("/api/calendar")
    def calendar(month: str, member: Member = Depends(signed_in)) -> dict[str, Any]:  # noqa: B008
        if not re.fullmatch(r"\d{4}-\d{2}", month):
            raise HTTPException(422, "month looks like 2026-10")
        with club(member.club_id) as (_, _, _, api):
            items = [views.calendar_item(i) for i in api.calendar() if i.date.isoformat().startswith(month)]
        return {"items": items, "connected": False}

    # ---------------------------------------------------------- knowledge

    def visible(store: KnowHowStore, club_id: str) -> list[KnowHowItem]:
        return [
            i
            for i in store.visible(club_id)
            if i.status in (ItemStatus.VERIFIED, ItemStatus.DISPUTED, ItemStatus.RETIRED)
        ]

    @app.get("/api/knowledge")
    def knowledge(tab: str = "", q: str = "", member: Member = Depends(signed_in)) -> list[dict[str, Any]]:  # noqa: B008
        with club(member.club_id) as (store, _, _, _):
            items = store.search(member.club_id, q, limit=50) if q.strip() else visible(store, member.club_id)
            rows = [views.knowledge(i, store.history(i.item_id), today()) for i in items]
        return [r for r in rows if not tab or r["tab"] == tab]

    @app.post("/api/knowledge/{item_id}/restore")
    def restore_fact(item_id: str, body: RestoreBody, member: Member = Depends(president)) -> dict[str, Any]:  # noqa: B008
        """Bring an expired fact back from the archive with a new end date, or none (D-115). President only."""
        with club(member.club_id) as (store, _, _, _):
            item = store.restore(item_id, member.actor(), clock(), body.valid_to)
            return views.knowledge(item, store.history(item.item_id), today())

    @app.get("/api/knowledge/{item_id}")
    def fact(item_id: str, member: Member = Depends(signed_in)) -> dict[str, Any]:  # noqa: B008
        with club(member.club_id) as (store, _, _, _):
            item = next((i for i in visible(store, member.club_id) if i.item_id == item_id), None)
            if item is None:
                raise HTTPException(404, "No such item.")
            return views.knowledge(item, store.history(item_id), today())

    def _revise(member: Member, item_id: str, **change: Any) -> dict[str, Any]:
        """A cabinet member's change applies at once as a new version; the old one stays in history (D-138)."""
        with club(member.club_id) as (store, _, _, _):
            item = store.revise(item_id, member.actor(), clock(), **change)
            return views.knowledge(item, store.history(item.item_id), today())

    @app.post("/api/knowledge/{item_id}/edit")
    def edit_fact(item_id: str, body: EditBody, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        return _revise(member, item_id, statement=body.text.strip())

    @app.post("/api/knowledge/{item_id}/retire")
    def retire_fact(item_id: str, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        return _revise(member, item_id, retire=True)

    @app.post("/api/knowledge/{item_id}/undo")
    def undo_fact(item_id: str, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        """Go back to the version before the last change, for example after an automatic update (D-138)."""
        return _revise(member, item_id, undo=True)

    # ------------------------------------------------------------- review

    _FILTER = {
        "facts": {"fact", "rule", "merge"},
        "disagreements": {"disagreement"},
        "documents": {"document"},
        "plans": {"plan"},
    }

    @app.get("/api/review")
    def review(filter: str = "all", member: Member = Depends(signed_in)) -> list[dict[str, Any]]:  # noqa: B008
        with club(member.club_id) as (store, _, _, _):
            cards = [
                views.review_card(p, store.latest(p.target_item) if p.target_item else None)
                for p in store.pending.values()
            ]
        wanted = _FILTER.get(filter)
        return [c for c in cards if wanted is None or c["type"] in wanted]

    @app.post("/api/review/{proposal_id}")
    def decide(proposal_id: str, body: DecisionBody, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        with club(member.club_id) as (store, _, _, _):
            proposal = store.pending.get(proposal_id)
            if proposal is None:
                raise HTTPException(404, "Nothing to review with this id.")
            card = views.review_card(proposal)
            choice = {"keep_a": "approve", "merge": "approve", "keep_b": "reject"}.get(body.decision, body.decision)
            if body.edited_text and choice == "approve":
                choice = "edit"  # the Edit dialog sends its text with a plain approve; it must not be dropped (F-245)
            both = choice in {"both", "keep_both"}
            if choice == "both" and not (body.reason or "").strip():
                raise HTTPException(422, "Explain when both versions are true.")
            edited = None
            if choice == "edit":
                if not body.edited_text:
                    raise HTTPException(422, "Write the corrected fact first.")
                edited = proposal.candidate.model_copy(update={"statement": body.edited_text})
            if body.shared is not None and choice != "reject":
                if proposal.candidate.kind is Kind.RULE and not body.shared:
                    raise HTTPException(422, "AUB rules are always shared with every club.")
                edited = rescoped(edited or proposal.candidate, member.club_id, shared=body.shared)
                if edited == proposal.candidate:
                    edited = None
            if both:
                # Keep the known fact as it is and add this one next to it, with the context when one was given.
                note = (body.reason or "").strip()
                if note:
                    base = edited or proposal.candidate
                    edited = base.model_copy(update={"statement": f"{base.statement} Context: {note}"[:1500]})
                store.keep_both(proposal.proposal_id, edited, body.reason, member.actor(), clock())
                outcome = None
            else:
                decision = {
                    "approve": VerifyDecision.ACCEPT,
                    "reject": VerifyDecision.REJECT,
                    "edit": VerifyDecision.ACCEPT_EDITED,
                }[choice]
                if edited is not None and decision is VerifyDecision.ACCEPT:
                    decision = VerifyDecision.ACCEPT_EDITED  # only the sharing changed
                outcome = store.verify(
                    VerifyRequest(proposal=proposal, decision=decision, edited_candidate=edited, reason=body.reason),
                    member.actor(),
                    clock(),
                )
            if outcome is not None and outcome.data is None:
                raise HTTPException(409, "This needs another cabinet member's decision first.")
        card["status"] = "rejected" if choice == "reject" else "approved"
        card["decided_at"] = clock().isoformat()
        return card

    # ------------------------------------------------------------- cabinet

    @app.get("/api/cabinet")
    def cabinet_list(member: Member = Depends(signed_in)) -> list[dict[str, str]]:  # noqa: B008
        return [m.view() for m in members.of_club(member.club_id)]

    @app.post("/api/cabinet", status_code=201)
    def add_member(body: MemberBody, member: Member = Depends(president)) -> dict[str, str]:  # noqa: B008
        if members.by_email(body.email) is not None:
            raise HTTPException(409, "This e-mail is already on a cabinet list.")
        try:
            return members.add(member.club_id, body.name, body.email, body.role).view()
        except ValueError as err:
            raise HTTPException(422, str(err)) from None

    @app.delete("/api/cabinet", status_code=204)
    def remove_member(body: RemoveBody = Body(...), member: Member = Depends(president)) -> None:  # noqa: B008
        if body.member_id == member.member_id:
            raise HTTPException(422, "You can't remove yourself; hand over the presidency first.")
        if not members.remove(member.club_id, body.member_id):
            raise HTTPException(404, "No such member in your club.")

    @app.get("/api/handover/{role}")
    def handover(role: Role, member: Member = Depends(signed_in)) -> dict[str, Any]:  # noqa: B008
        with club(member.club_id) as (store, _, _, _):
            request = HandoverRequest(club_id=member.club_id, role=role, outgoing=member.member_id, as_of=today())
            return dict(guide_view(build_handover(store, request), store.current(member.club_id, today())))

    # --------------------------------------------------------------- usage

    @app.get("/api/usage")
    def usage(member: Member = Depends(signed_in)) -> dict[str, Any]:  # noqa: B008
        month = clock().strftime("%Y-%m")
        with club(member.club_id) as (_, _, _, api):
            calls, cost = api.usage(month)
        feature = {"name": "Event planning", "calls": calls, "cost_usd": float(cost)}
        return {
            "month": month,
            "cost_usd": float(cost),
            "calls": calls,
            "calls_label": "Planner steps",
            "most_expensive_feature": feature["name"] if calls else "",
            "by_feature": [feature] if calls else [],
            **usage_details(config.data_dir, member.club_id, month),
        }

    # ---------------------------------------------------- learning (T-18)

    def learn(
        member: Member, sources: list[Untrusted], event_id: str | None = None, extra: list[Candidate] | None = None
    ) -> list[str]:
        """Proposed facts go to Review; nothing is saved as known until a person approves (D-41)."""
        with club(member.club_id) as (store, _, _, _):
            learner = Learner(model_client(), store)
            result = learner.learn(
                CaptureRequest(club_id=member.club_id, sources=sources, context_event=event_id),
                today(),
                load_settings().new_budget(),
                extra,
            )
        return [p.proposal_id for p in result.proposals]

    def untrusted(text: str, kind: SourceKind, source_id: str, locator: str | None = None) -> Untrusted:
        return Untrusted(
            content=text,
            source=SourceRef(kind=kind, source_id=source_id[:200], locator=locator, observed_at=clock()),
        )

    @app.post("/api/chat/teach")
    def teach(body: AnswerBody, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        ids = learn(
            member, [untrusted(body.text, SourceKind.USER_INPUT, f"chat/{member.member_id}/{clock():%Y%m%d%H%M%S}")]
        )
        if not ids:
            return {"kind": "learned", "text": "I didn't find a fact to keep in that message.", "review_id": ""}
        with club(member.club_id) as (store, _, _, _):
            first = store.pending[ids[0]].candidate.statement
        more = f" (+{len(ids) - 1} more)" if len(ids) > 1 else ""
        return {"kind": "learned", "text": f"New fact sent for review: {first}{more}", "review_id": ids[0]}

    class AfterEventBody(BaseModel):
        answers: dict[str, str]

    @app.post("/api/events/{event_id}/after-event")
    def after_event(event_id: str, body: AfterEventBody, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        with club(member.club_id) as (_, directory, _, api):
            event = api.event(event_id)
            if event is None:
                raise HTTPException(404, "No such event.")
            answers = {k.strip()[:200]: v.strip()[:2000] for k, v in body.answers.items() if v.strip()}
            if not answers:
                raise HTTPException(422, "Answer at least one question.")
            text = "\n".join(f"{q}: {a}" for q, a in answers.items())
            record = directory.event(event_id)
            if record is not None:
                directory.put_event(record.model_copy(update={"status": EventStatus.CLOSED, "outcome": text[:1000]}))
        ids = learn(member, [untrusted(text, SourceKind.RETROSPECTIVE, f"after-event/{event_id}")], event_id)
        draft = {
            "type": "impact_report",
            "text": f"Impact report: {event.spec.title or event_id}\n\n{text}",
            "template_version": "plain-v1",
            "based_on": [],
            "state": "draft",
        }
        return {"draft": draft, "review_count": len(ids)}

    @app.post("/api/documents")
    async def upload(file: UploadFile, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        name = (file.filename or "document")[:120]
        kind = name.lower().rsplit(".", 1)[-1]
        limit = MAX_PDF_UPLOAD if kind == "pdf" else MAX_UPLOAD
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"The file is too big ({limit // (1024 * 1024)} MB at most).")
        note = ""
        extra: list[Candidate] = []
        if kind == "xlsx":
            try:
                book = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            except Exception:
                raise HTTPException(422, "This spreadsheet can't be opened.") from None
            rows: list[list[object]] = [list(r) for ws in book.worksheets[:3] for r in ws.iter_rows(values_only=True)]
            extra = price_list(rows, member.club_id, name, clock())
            text = "" if extra else rows_to_text(rows)
        elif kind == "pdf":
            try:
                pdf = read_pdf(data)
            except DocumentError as error:
                raise HTTPException(422, str(error)) from None
            text = pdf.text
            if pdf.images:
                note = f" Pictures in the file ({pdf.images}) are not read, only its text."
            if not text.strip():
                raise HTTPException(422, "This PDF has no text, only pictures. ClubOps does not read pictures yet.")
        elif kind in {"txt", "md", "csv", "eml"}:
            text = data.decode("utf-8", errors="replace")
        else:
            raise HTTPException(422, "Upload a .pdf, .txt, .md, .csv, .eml or .xlsx file (save Word files as PDF).")
        pieces = split_text(text) if text.strip() else []
        if len(pieces) > MAX_PIECES:
            pieces, note = pieces[:MAX_PIECES], note + f" Only the first {MAX_PIECES} pieces were read."
        sources = [
            untrusted(piece, SourceKind.DOCUMENT, f"upload/{name}#{n}", f"{name} (part {n}/{len(pieces)})")
            for n, piece in enumerate(pieces, 1)
        ]
        if not sources and not extra:
            return document_view(name, 0)
        if not sources:
            with club(member.club_id) as (store, _, _, _):
                result = Learner(None, store).learn(
                    CaptureRequest(
                        club_id=member.club_id, sources=[untrusted(name, SourceKind.DOCUMENT, f"upload/{name}")]
                    ),
                    today(),
                    None,
                    extra,
                )
            return document_view(name, len(result.proposals))
        found: list[str] = []
        for start in range(0, len(sources), 3):  # three pieces per read: one read answers at most 20 facts
            found += learn(member, sources[start : start + 3], extra=extra if start == 0 else None)
        return document_view(name, len(found), note)

    def document_view(name: str, count: int, note: str = "") -> dict[str, Any]:
        return {
            "item_id": f"doc-{uuid.uuid4().hex[:8]}",
            "title": name,
            "statement": (
                f"{count} fact{'s' if count != 1 else ''} sent for review" if count else "No facts found in this file."
            )
            + note,
            "tab": "documents",
            "kind": "document",
            "scope": "club",
            "sources": [],
            "last_checked": today().isoformat(),
            "status": "current",
            "history": [],
            "used_in": [],
        }

    # -------------------------------------------------- not built yet (501)

    @app.post("/api/chat/ask")
    def ask(member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        """Until the chatbot (T-17) exists: say so honestly, with who to ask (D-49). Cabinet only: the read-only
        adviser must not start a question that will cost a model call once the chatbot is on (F-217)."""
        return {
            "known": False,
            "text": "The chatbot isn't switched on yet, so I can't answer from the club's memory.",
            "citations": [],
            "basis": "none",
            "ask": {"who": "the club president", "role": None},
            "look_in": None,
        }

    # ------------------------------------------------------------- OSA inbox (T-47)

    inbox = PendingInbox(config.data_dir / "inbox.db")
    inbox_notes = InboxNotes(config.data_dir / "inbox-notes.db")
    inbox_ledger = InboxLedger(config.data_dir / "inbox-ledger.db")

    def _summary(message_id: str, request: CaptureRequest) -> dict[str, str]:
        """Metadata only: subject, date and who forwarded it. The body is shown nowhere before Review."""
        text = request.sources[0].content if request.sources else ""
        lines = {k: v.strip() for k, _, v in (line.partition(":") for line in text.splitlines()[:5])}
        return {
            "id": message_id,
            "subject": lines.get("Subject", "")[:200],
            "date": lines.get("Date", "")[:40],
            "forwarded_by": lines.get("Forwarded by", "")[:200],
        }

    @app.get("/api/inbox")
    def inbox_list(member: Member = Depends(cabinet)) -> list[dict[str, str]]:  # noqa: B008
        """Forwarded e-mails waiting for this club. Free: nothing has been read by a model yet."""
        return [_summary(mid, req) for mid, req in inbox.pending(member.club_id)]

    @app.get("/api/inbox/skipped")
    def inbox_skipped(member: Member = Depends(cabinet)) -> list[dict[str, str]]:  # noqa: B008
        """Forwarded e-mails the free checks refused, with the reason in plain words. Never read."""
        return inbox_notes.skipped(member.club_id)

    @app.post("/api/inbox/{message_id}/allow")
    def inbox_allow(message_id: str, member: Member = Depends(cabinet)) -> dict[str, bool]:  # noqa: B008
        """Release an e-mail that was skipped only because its original sender is not on the OSA list. It joins
        the waiting list; nothing is read until someone confirms the paid read, and its cards say the sender is
        unlisted (D-136)."""
        taken = inbox_notes.take_held(message_id, member.club_id)
        if taken is None:
            raise HTTPException(404, "No e-mail with that id can be released for your club.")
        request, fingerprint, audience = taken
        if inbox.enqueue(message_id, request):
            inbox_notes.accept(message_id, member.club_id, fingerprint, audience, unlisted=True)
        return {"waiting": True}

    @app.post("/api/inbox/{message_id}/capture")
    def inbox_capture(message_id: str, member: Member = Depends(cabinet)) -> dict[str, Any]:  # noqa: B008
        """One paid model read, started by a person. Proposals go to Review; the e-mail leaves the queue
        only when the read worked, so a failed read can be retried (F-214). Nothing is approved here (D-41)."""
        waiting = dict(inbox.pending(member.club_id))
        request = waiting.get(message_id)
        if request is None or request.club_id != member.club_id:
            raise HTTPException(404, "No waiting e-mail with that id for your club.")
        fingerprint = inbox_notes.fingerprint(message_id, member.club_id)
        if fingerprint is None:  # queued without J-22's checks: never paid for (D-114)
            raise HTTPException(409, "This e-mail has not passed the inbox checks. Fetch the inbox again.")
        token = inbox_ledger.claim_read(fingerprint)
        if token is None:
            raise HTTPException(409, "This e-mail is already being read, or was read for another club.")
        try:
            with club(member.club_id) as (store, _, _, _):
                result = Learner(model_client(), store).learn(
                    request,
                    today(),
                    load_settings().new_budget(),
                    audience=inbox_notes.audience(message_id, member.club_id),
                    unlisted_sender=inbox_notes.is_unlisted(message_id, member.club_id),
                )
        except BaseException:
            inbox_ledger.release_read(fingerprint, token)
            raise
        if result.sources_failed:
            inbox_ledger.release_read(fingerprint, token)
            raise HTTPException(502, "The e-mail could not be read this time. It is still waiting; try again.")
        inbox_ledger.mark_read(fingerprint, token)
        inbox.mark_processed(message_id, member.club_id)
        # Clean facts from trusted OSA mail apply at once; anything odd waits in Review (D-138)
        with club(member.club_id) as (store, _, _, _):
            applied = [
                p.proposal_id for p in result.proposals if store.auto_apply(p.proposal_id, member.club_id, clock())
            ]
        # `skipped` is a list of plain reasons, as docs/api.md says; the web screen rejects a number (F-239)
        return {
            "proposals": [p.proposal_id for p in result.proposals if p.proposal_id not in applied],
            "applied": applied,
            "skipped": ["The model could not use this content."] * result.sources_skipped,
        }

    # ----------------------------------------------------------- new-club setup (C-21)

    def setup_actor(member: Member = Depends(signed_in)) -> Actor:  # noqa: B008
        """The session's own actor. The club never comes from the body; the router checks president + CSRF."""
        return member.actor()

    def setup_capture(request: CaptureRequest) -> CaptureResult:
        """The public learner's capture: proposals only. Nothing is approved here (D-41)."""
        with club(request.club_id) as (store, _, _, _):
            return Learner(model_client(), store).capture(request, today(), load_settings().new_budget())

    def setup_submit(proposed: KnowHowProposal) -> None:
        """Queue one proposal for Review, idempotently by id, and never verify it.

        A retry after a partial queue failure must not duplicate a card, nor bring back one already
        approved. A proposal the president *rejected* leaves no record in the store, so that one case
        can still reappear once (F-201).
        """
        with club(proposed.candidate.club_id or "invalid") as (store, _, _, _):
            if proposed.proposal_id in store.pending:
                return  # already waiting for a decision
            if store.latest(proposed.candidate.item_id) is not None:
                return  # already approved into the club's knowledge
            store.submit(proposed)

    def setup_rules_count(club_id: str, on: date) -> int:
        """Approved AUB-wide rules the club already has: read, never copied into the club (C-21)."""
        with club(club_id) as (store, _, _, _):
            return sum(i.scope is Scope.AUB and i.kind is Kind.RULE for i in store.current(club_id, on))

    # Tests swap in synthetic callbacks here, never by deleting routes: in FastAPI 0.16x a route removed
    # from app.router.routes is no longer listed but is still served (D-112).
    overrides = dict(setup_overrides or {})
    unknown = set(overrides) - {"capture", "submit", "rules_count"}
    if unknown:
        raise ValueError(f"unknown setup overrides: {sorted(unknown)}")
    app.include_router(
        setup_router(
            setup_service,
            actor_dependency=setup_actor,
            capture=overrides.get("capture", setup_capture),
            submit=overrides.get("submit", setup_submit),
            rules_count=overrides.get("rules_count", setup_rules_count),
            clock=clock,
        )
    )

    def not_yet(task: str) -> Callable[..., Any]:
        def handler(member: Member = Depends(signed_in)) -> None:  # noqa: B008
            raise HTTPException(501, f"This part of ClubOps isn't built yet ({task}).")

        return handler

    for method, path, task in (("POST", "/api/events/{event_id}/drafts/{draft_type}", "J-07"),):
        app.add_api_route(path, not_yet(task), methods=[method])

    return app


# ------------------------------------------------------------- event edits

_YES = {"yes": True, "no": False, "": None}
_AUD = {"AUB students only": Audience.AUB_ONLY, "AUB and outside guests": Audience.AUB_AND_GUESTS}


def apply_fields(spec: EventSpec, changes: dict[str, str]) -> EventSpec:
    """Apply the event page's edits (text fields) to the event details; bumps the revision."""
    values = views.fields(spec) | {k: v.strip() for k, v in changes.items() if k in views.fields(spec)}
    data = spec.model_dump()
    data["title"] = values["title"] or None
    data["description"] = values["description"] or None
    if values["venue"]:
        kind = (
            VenueKind.GREEN_FIELD
            if "green field" in values["venue"].lower()
            else (spec.venue.kind if spec.venue else VenueKind.OTHER_ON_CAMPUS)
        )
        data["venue"] = Venue(kind=kind, name=values["venue"][:120]).model_dump()
    data["audience"] = _AUD.get(values["audience"])
    for key, field in (("has_prizes", "has_prizes"), ("catering", "has_catering")):
        if values[key].lower() not in _YES:
            raise ValueError(f"{key} is yes or no")
        data[field] = _YES[values[key].lower()]
    if values["date"] and values["time"]:
        day = date.fromisoformat(values["date"])
        start = datetime.fromisoformat(f"{day}T{values['time']}").replace(tzinfo=views.BEIRUT)
        end_time = values["end_time"] or values["time"]
        data["start"] = start
        data["end"] = datetime.fromisoformat(f"{day}T{end_time}").replace(tzinfo=views.BEIRUT)
    data["revision"] = spec.revision + 1
    return EventSpec.model_validate(data)


def build() -> FastAPI:
    """The app uvicorn serves: settings from the environment."""
    return create_app(load_api_config())
