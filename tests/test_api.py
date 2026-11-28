"""The HTTP API (T-22): sign-in, club separation, the plan -> approve -> calendar flow, knowledge, review,
cabinet. A scripted model stands in for the real one. Synthetic people and events only."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from scripts.load_rulebook import load

from clubops.agent.planner import EventFacts, NextStep, Planner, RunState, Tool
from clubops.api.app import ApiConfig, create_app
from clubops.api.security import MemberStore
from clubops.api.setup import QUESTIONS
from clubops.capabilities.runner import Usage
from clubops.contracts.common import Role
from clubops.contracts.event import Audience, EventType, Venue, VenueKind
from clubops.knowhow.directory import Directory
from clubops.knowhow.store import KnowHowStore
from clubops.model.budget import Budget
from tests.factories import item, proposal

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
START = datetime(2026, 11, 20, 14, 0, tzinfo=UTC)  # 16:00 in Beirut
HEADERS = {"X-Requested-With": "ClubOps"}


def step(tool: Tool, **kw: Any) -> NextStep:
    return NextStep(tool=tool, say=kw.pop("say", f"doing {tool}"), **kw)


FACTS = EventFacts(
    title="Campus fun run",
    event_type=EventType.SPORT,
    start=START,
    end=START.replace(hour=17),
    venue=Venue(kind=VenueKind.GREEN_FIELD, name="Green Field"),
    audience=Audience.AUB_AND_GUESTS,
    has_prizes=False,
    has_catering=False,
)
PLAN = [
    step(Tool.UPDATE_EVENT, facts=FACTS),
    step(Tool.CHECK_RULES),
    step(Tool.PLAN_TASKS),
    step(Tool.FINISH),
]


class Script:
    def __init__(self, steps: list[NextStep]) -> None:
        self.steps = list(steps)

    def __call__(self, prompt: str, budget: Budget) -> NextStep:
        budget.check()
        budget.charge(Usage(cost_usd=Decimal("0.001")))
        return self.steps.pop(0)


class Scripts:
    """One script per agent run, in order."""

    def __init__(self) -> None:
        self.queue: list[list[NextStep]] = []

    def factory(self) -> Callable[[KnowHowStore, Directory, Callable[[RunState], None]], Planner]:
        def make(store: KnowHowStore, directory: Directory, on_step: Callable[[RunState], None]) -> Planner:
            return Planner(Script(self.queue.pop(0) if self.queue else []), store, directory, on_step=on_step)

        return make


@pytest.fixture
def scripts() -> Scripts:
    return Scripts()


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    load(tmp_path, None)  # the AUB rulebook, as in production
    people = MemberStore(tmp_path)
    people.add("running-club", "Test President", "tp01@mail.aub.edu", Role.PRESIDENT)
    people.add("running-club", "Test Events", "te02@mail.aub.edu", Role.EVENTS)
    people.add("running-club", "Test Adviser", "ta03@aub.edu.lb", Role.ADVISER)
    people.add("asme", "Other President", "op04@mail.aub.edu", Role.PRESIDENT)
    people.close()
    return tmp_path


def google(email: str, aud: str = "client-123") -> httpx.MockTransport:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"aud": aud, "email": email, "email_verified": "true"})

    return httpx.MockTransport(handle)


def make_client(data_dir: Path, scripts: Scripts, **kw: Any) -> TestClient:
    config = ApiConfig(
        data_dir=data_dir,
        session_secret="test-secret",  # noqa: S106 (test only)
        dev_login=True,
        cookie_secure=False,
        google_client_id="client-123",
    )
    return TestClient(create_app(config, scripts.factory(), clock=lambda: NOW, **kw))


@pytest.fixture
def client(data_dir: Path, scripts: Scripts) -> Iterator[TestClient]:
    with make_client(data_dir, scripts) as c:
        yield c


def sign_in(c: TestClient, email: str = "tp01@mail.aub.edu") -> TestClient:
    r = c.post("/api/auth/dev", json={"email": email}, headers=HEADERS)
    assert r.status_code == 200, r.text
    return c


def plan(c: TestClient, scripts: Scripts, steps: list[NextStep] = PLAN) -> str:
    scripts.queue.append(steps)
    r = c.post("/api/events/plan", json={"description": "Fun run on Green Field, open to friends"}, headers=HEADERS)
    assert r.status_code == 202, r.text
    return str(r.json()["run_id"])


# -------------------------------------------------------------- sign-in


def test_nothing_is_readable_without_signing_in(client: TestClient) -> None:
    for path in ("/api/me", "/api/events", "/api/knowledge", "/api/review", "/api/cabinet", "/api/usage"):
        assert client.get(path).status_code == 401


def test_changes_need_the_clubops_header(client: TestClient) -> None:
    sign_in(client)
    assert client.post("/api/events/plan", json={"description": "A run"}).status_code == 403


def test_google_sign_in_matches_the_cabinet_list(data_dir: Path, scripts: Scripts) -> None:
    with make_client(data_dir, scripts, google_transport=google("te02@mail.aub.edu")) as c:
        r = c.post("/api/auth/google", json={"credential": "x" * 20}, headers=HEADERS)
        assert r.status_code == 200 and r.json()["role"] == "events"
        assert c.get("/api/me").json()["user"]["email"] == "te02@mail.aub.edu"
    with make_client(data_dir, scripts, google_transport=google("stranger@mail.aub.edu")) as c:
        assert c.post("/api/auth/google", json={"credential": "x" * 20}, headers=HEADERS).status_code == 403
    with make_client(data_dir, scripts, google_transport=google("te02@mail.aub.edu", aud="someone-else")) as c:
        assert c.post("/api/auth/google", json={"credential": "x" * 20}, headers=HEADERS).status_code == 403


def test_a_forged_cookie_is_refused(client: TestClient) -> None:
    client.cookies.set("clubops_session", "eyJtIjoibS10ZXN0In0.forged")
    assert client.get("/api/me").status_code == 401


def test_dev_sign_in_is_off_in_production(data_dir: Path, scripts: Scripts) -> None:
    config = ApiConfig(data_dir=data_dir, session_secret="s", dev_login=False)  # noqa: S106
    with TestClient(create_app(config, scripts.factory())) as c:
        assert c.post("/api/auth/dev", json={"email": "tp01@mail.aub.edu"}, headers=HEADERS).status_code == 404


# ------------------------------------------------------- plan and approve


def test_plan_then_approve_sends_the_tasks_to_the_calendar(client: TestClient, scripts: Scripts) -> None:
    sign_in(client)
    run_id = plan(client, scripts)
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "done" and [s["tool"] for s in run["steps"]][-1] == "finish"
    event_id = run["event_id"]

    events = client.get("/api/events").json()
    assert [e["event_id"] for e in events] == [event_id]
    assert events[0]["status"] == "planned" and not events[0]["plan_outdated"]

    detail = client.get(f"/api/events/{event_id}").json()
    assert detail["fields"]["time"] == "16:00" and detail["fields"]["venue"] == "Green Field"
    names = {a["approval_id"] for a in detail["approvals"]}
    assert {"osa-proposal", "hostler-booking", "guest-approval"} <= names
    task = next(t for t in detail["tasks"] if t["requirement_id"] == "osa-proposal")
    assert task["due"] == "2026-11-06" and task["source"]["item_id"] == "kh-aub-proposal"

    assert (
        client.post(f"/api/events/{event_id}/approve-plan", json={"revision": 99}, headers=HEADERS).status_code == 409
    )
    approved = client.post(
        f"/api/events/{event_id}/approve-plan", json={"revision": detail["revision"]}, headers=HEADERS
    )
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    november = client.get("/api/calendar?month=2026-11").json()["items"]
    assert any(i["item_id"] == f"{event_id}/event" for i in november)
    assert any(i["item_id"] == f"{event_id}/impact-form" for i in november)


def test_a_run_waits_for_an_answer_then_carries_on(client: TestClient, scripts: Scripts) -> None:
    sign_in(client)
    run_id = plan(client, scripts, [step(Tool.ASK_USER, question="Which day?")])
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "waiting_for_user"
    scripts.queue.append(PLAN)
    after = client.post(f"/api/runs/{run_id}/answer", json={"text": "20 November"}, headers=HEADERS).json()
    assert after["status"] == "done"
    assert len(client.get("/api/events").json()) == 1
    metrics = client.get("/api/usage").json()["run_metrics"]
    assert metrics["successful_plans"] == 1 and metrics["planner_steps"] == 5
    assert metrics["cost_usd"] == pytest.approx(0.005)


def test_editing_the_event_makes_the_plan_outdated(client: TestClient, scripts: Scripts) -> None:
    sign_in(client)
    event_id = client.get(f"/api/runs/{plan(client, scripts)}").json()["event_id"]
    edited = client.patch(f"/api/events/{event_id}", json={"fields": {"has_prizes": "yes"}}, headers=HEADERS).json()
    assert edited["plan_outdated"] and edited["fields"]["has_prizes"] == "yes"
    r = client.post(f"/api/events/{event_id}/approve-plan", json={"revision": edited["revision"]}, headers=HEADERS)
    assert r.status_code == 409  # the plan is for the old details


def test_a_task_can_be_marked_done(client: TestClient, scripts: Scripts) -> None:
    sign_in(client)
    event_id = client.get(f"/api/runs/{plan(client, scripts)}").json()["event_id"]
    task_id = f"{event_id}/osa-proposal"
    r = client.patch(f"/api/tasks/{task_id.replace('/', '%2F')}", json={"state": "done"}, headers=HEADERS)
    assert r.status_code == 200 and r.json()["state"] == "done"
    assert client.get("/api/events").json()[0]["tasks_done"] == 1


# --------------------------------------------------------- who may do what


def test_the_adviser_can_read_but_not_plan(client: TestClient, scripts: Scripts) -> None:
    sign_in(client, "ta03@aub.edu.lb")
    assert client.get("/api/events").status_code == 200
    assert client.post("/api/events/plan", json={"description": "A run"}, headers=HEADERS).status_code == 403


def test_one_club_cannot_see_another_clubs_runs_or_events(data_dir: Path, scripts: Scripts) -> None:
    with make_client(data_dir, scripts) as ours:
        sign_in(ours)
        run_id = plan(ours, scripts)
        event_id = ours.get(f"/api/runs/{run_id}").json()["event_id"]
    with make_client(data_dir, scripts) as theirs:
        sign_in(theirs, "op04@mail.aub.edu")
        assert theirs.get(f"/api/runs/{run_id}").status_code == 404
        assert theirs.get(f"/api/events/{event_id}").status_code == 404
        assert theirs.get("/api/events").json() == []


def test_only_the_president_changes_the_cabinet(client: TestClient) -> None:
    sign_in(client, "te02@mail.aub.edu")
    new = {"name": "New Member", "email": "nm05@mail.aub.edu", "role": "treasurer"}
    assert client.post("/api/cabinet", json=new, headers=HEADERS).status_code == 403
    sign_in(client)
    added = client.post("/api/cabinet", json=new, headers=HEADERS)
    assert added.status_code == 201
    assert any(m["email"] == "nm05@mail.aub.edu" for m in client.get("/api/cabinet").json())
    me = client.get("/api/me").json()["user"]["member_id"]
    gone = client.request("DELETE", "/api/cabinet", json={"member_id": me}, headers=HEADERS)
    assert gone.status_code == 422  # not yourself
    gmail = client.post("/api/cabinet", json={**new, "email": "someone@gmail.com"}, headers=HEADERS)
    assert gmail.status_code == 201  # any Google account the president vouches for (D-68)
    assert client.post("/api/cabinet", json={**new, "email": "not-an-email"}, headers=HEADERS).status_code == 422


# ------------------------------------------------------- knowledge, review


def test_the_rulebook_shows_in_knowledge(client: TestClient) -> None:
    sign_in(client)
    rules = client.get("/api/knowledge?tab=rules").json()
    assert len(rules) == 27 and all(r["scope"] == "aub" for r in rules)
    one = client.get("/api/knowledge/kh-aub-proposal").json()
    assert one["lead_time_days"] == 10 and one["sources"][0]["authority"] == "official_document"
    assert client.get("/api/knowledge?q=sponsor").json()


def test_a_learned_fact_waits_in_review_until_a_person_approves(client: TestClient, data_dir: Path) -> None:
    from clubops.knowhow.backends import open_club_store_backend

    store = KnowHowStore(open_club_store_backend(data_dir, "running-club"))
    store.submit(proposal(item("kh-blk-notice", title="BLK needs 10 days' notice")))
    store.close()

    sign_in(client)
    cards = client.get("/api/review").json()
    assert [c["id"] for c in cards] == ["p-1"]
    assert client.get("/api/knowledge/kh-blk-notice").status_code == 404  # not saved yet
    decided = client.post("/api/review/p-1", json={"decision": "approve"}, headers=HEADERS)
    assert decided.status_code == 200 and decided.json()["status"] == "approved"
    assert client.get("/api/knowledge/kh-blk-notice").status_code == 200
    assert client.get("/api/review").json() == []


# ------------------------------------------------------ usage and the rest


def test_usage_adds_up_the_agent_runs(client: TestClient, scripts: Scripts) -> None:
    sign_in(client)
    plan(client, scripts)
    usage = client.get("/api/usage").json()
    assert usage["month"] == "2026-10" and usage["calls"] == 4 and usage["cost_usd"] == pytest.approx(0.004)
    assert usage["run_metrics"]["successful_plans"] == 1
    assert usage["run_metrics"]["cost_per_successful_plan"] == pytest.approx(0.004)
    assert usage["trace_metrics_available"] is False


def test_chat_unknown_says_who_to_ask(data_dir: Path, scripts: Scripts) -> None:
    from clubops.contracts.knowhow import Answer, AskWho
    from tests.test_chat_ask import FakeModel

    model = FakeModel(Answer(known=False, text="Not sure", basis="none", ask=AskWho(who="Club president")))
    client = make_client(data_dir, scripts, model_client=lambda: model)
    sign_in(client)
    assert client.get("/api/handover/president").status_code == 200
    answer = client.post("/api/chat/ask", json={"text": "Who books Hostler?"}, headers=HEADERS).json()
    assert answer["known"] is False and answer["ask"]["who"]  # never a made-up answer (D-49)


# ----------------------------------------------------------- new-club setup (C-21)


def test_the_real_app_serves_setup_and_knows_which_clubs_are_set_up(client: TestClient) -> None:
    """The production route, not the test adapter: a new club gets the questions, the club set up by hand
    before C-21 is not asked again (D-112)."""
    sign_in(client)  # the Running Club president
    assert client.get("/api/me").json()["club"]["setup_complete"] is True

    sign_in(client, "op04@mail.aub.edu")  # a president of a club that has never been set up
    assert client.get("/api/me").json()["club"]["setup_complete"] is False
    step = client.post("/api/setup/next", json={}, headers=HEADERS)
    assert step.status_code == 200, step.text
    body = step.json()
    assert body["index"] == 1 and body["total"] == len(QUESTIONS) and not body["done"]
    assert body["question"] and body["rules_count"] > 0  # shared AUB rules, read not copied


def test_setup_skips_without_calling_the_model(client: TestClient) -> None:
    """A skip moves on and never spends: nothing reaches the model (C-21)."""
    sign_in(client, "op04@mail.aub.edu")
    client.post("/api/setup/next", json={}, headers=HEADERS)
    step = client.post("/api/setup/next", json={"answer": "[skip]"}, headers=HEADERS)
    assert step.status_code == 200, step.text
    assert step.json()["index"] == 2
    assert client.get("/api/usage").json()["calls"] == 0


def test_setup_is_for_the_president_only(client: TestClient) -> None:
    sign_in(client, "te02@mail.aub.edu")  # a cabinet member who is not the president
    assert client.post("/api/setup/next", json={}, headers=HEADERS).status_code in (401, 403)


@pytest.mark.parametrize("end", [None, "2026-12-31"])
def test_chat_answers_with_dated_sources(data_dir: Path, scripts: Scripts, end: str | None) -> None:
    from datetime import date

    from clubops.knowhow.backends import open_club_store_backend
    from tests.factories import verified
    from tests.test_chat_ask import FakeModel, known

    fact = verified(item(valid_to=date.fromisoformat(end) if end else None))
    store = KnowHowStore(open_club_store_backend(data_dir, "running-club"))
    store.backend.append(fact)
    store.close()
    model = FakeModel(known([fact.item_id]))
    with make_client(data_dir, scripts, model_client=lambda: model) as c:
        sign_in(c)
        response = c.post("/api/chat/ask", json={"text": "Green Field", "club_id": "asme"}, headers=HEADERS)
        assert response.status_code == 200
        answer = response.json()
        assert answer["kind"] == "answer" and answer["known"]
        source = answer["citations"][0]
        assert source["item_id"] == fact.item_id
        assert source["valid_to"] == end
        assert (f"Valid through {end}" if end else "No end date") in source["label"]
        assert model.called

        model.called = False
        sign_in(c, "op04@mail.aub.edu")
        answer = c.post("/api/chat/ask", json={"text": "Green Field"}, headers=HEADERS).json()
        assert not answer["known"] and answer["ask"]["who"]
        import json

        assert fact.item_id not in [f["id"] for f in json.loads(model.user)["facts"]]


def test_chat_access_and_invalid_input_never_call_model(data_dir: Path, scripts: Scripts) -> None:
    def forbidden_model() -> None:
        pytest.fail("Unauthorized or invalid chat must not construct a model")

    with make_client(data_dir, scripts, model_client=forbidden_model) as c:
        assert c.post("/api/chat/ask", json={"text": "Green Field"}, headers=HEADERS).status_code == 401
        sign_in(c, "ta03@aub.edu.lb")
        assert c.post("/api/chat/ask", json={"text": "Green Field"}, headers=HEADERS).status_code == 403
        sign_in(c)
        for body in ({}, {"text": ""}, {"text": "x" * 501}):
            assert c.post("/api/chat/ask", json=body, headers=HEADERS).status_code == 422
        hi = c.post("/api/chat/ask", json={"text": "hi"}, headers=HEADERS)  # F-335: a greeting is answered, not refused
        assert hi.status_code == 200 and hi.json()["known"] is False and hi.json()["kind"] == "unknown"
        assert c.post("/api/chat/ask", json={"text": "Green Field"}).status_code == 403


@pytest.mark.parametrize("change", [{"valid_to": "2026-09-30"}, {"valid_from": "2027-01-01"}, {"status": "retired"}])
def test_chat_excludes_inactive_store_facts(data_dir: Path, scripts: Scripts, change: dict[str, str]) -> None:
    import json
    from datetime import date

    from clubops.contracts.knowhow import ItemStatus
    from clubops.knowhow.backends import open_club_store_backend
    from tests.factories import verified
    from tests.test_chat_ask import FakeModel, known

    changes = {k: ItemStatus(v) if k == "status" else date.fromisoformat(v) for k, v in change.items()}
    fact = verified(item()).model_copy(update=changes)
    store = KnowHowStore(open_club_store_backend(data_dir, "running-club"))
    store.backend.append(fact)
    store.close()
    model = FakeModel(known([fact.item_id]))
    with make_client(data_dir, scripts, model_client=lambda: model) as c:
        sign_in(c)
        answer = c.post("/api/chat/ask", json={"text": "Green Field"}, headers=HEADERS).json()
        assert not answer["known"]
        if model.called:
            assert fact.item_id not in [f["id"] for f in json.loads(model.user)["facts"]]
