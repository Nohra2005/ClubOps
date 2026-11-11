"""C-21 integration adapter: real auth/Review/SQLite, synthetic extraction.

app.py now wires the setup route itself. These tests run that production route with
synthetic capture/submit/rules callbacks, passed through create_app's setup_overrides
(never by deleting routes: FastAPI 0.16x keeps serving a removed route, D-112).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from scripts.load_rulebook import load

from clubops.api.app import ApiConfig, create_app
from clubops.api.security import MemberStore
from clubops.api.setup import QUESTIONS, SetupService
from clubops.contracts.common import Role
from clubops.contracts.knowhow import CaptureRequest, CaptureResult, Kind, KnowHowProposal, Scope
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore
from tests.factories import NOW, item, proposal

HEADERS = {"X-Requested-With": "ClubOps"}


class Adapter:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.captures: list[CaptureRequest] = []
        self.fail_after_queue = False

    def capture(self, request: CaptureRequest) -> CaptureResult:
        self.captures.append(request)
        candidate = item(
            "kh-setup-synthetic",
            club_id=request.club_id,
            title="Synthetic setup context",
            statement=request.sources[0].content.split("\nAnswer: ", 1)[1],
            sources=[request.sources[0].source.model_copy(update={"quote": request.sources[0].content[:500]})],
        )
        return CaptureResult(proposals=[proposal(candidate)], sources_seen=1, sources_skipped=0)

    def submit(self, proposed: KnowHowProposal) -> None:
        store = KnowHowStore(open_club_store_backend(self.data_dir, proposed.candidate.club_id or "invalid"))
        try:
            store.submit(proposed)
        finally:
            store.close()
        if self.fail_after_queue:
            self.fail_after_queue = False
            raise RuntimeError("synthetic failure after durable queue commit")

    def rules_count(self, club_id: str, on: date) -> int:
        store = KnowHowStore(open_club_store_backend(self.data_dir, club_id))
        try:
            return sum(it.scope is Scope.AUB and it.kind is Kind.RULE for it in store.current(club_id, on))
        finally:
            store.close()


def setup_app(data_dir: Path, adapter: Adapter) -> FastAPI:
    load(data_dir, None)
    people = MemberStore(data_dir)
    people.add("running-club", "Synthetic President", "president@example.com", Role.PRESIDENT)
    people.add("asme", "Synthetic Other President", "other@example.com", Role.PRESIDENT)
    people.close()
    return create_app(
        ApiConfig(data_dir, "synthetic-setup-secret", dev_login=True, cookie_secure=False),
        clock=lambda: NOW,
        setup_overrides={"capture": adapter.capture, "submit": adapter.submit, "rules_count": adapter.rules_count},
    )


def test_adapter_uses_real_auth_shared_rules_review_and_club_separation(tmp_path: Path) -> None:
    adapter = Adapter(tmp_path)
    rulebook = Path(__file__).resolve().parents[1] / "data/rulebook/aub-rules.json"
    expected_rules = len(json.loads(rulebook.read_text(encoding="utf-8")))
    assert expected_rules > 0
    with TestClient(setup_app(tmp_path, adapter)) as client:
        endpoint = "/api/setup/next"
        assert client.post(endpoint, json={}, headers=HEADERS).status_code == 401
        assert client.post("/api/auth/dev", json={"email": "president@example.com"}, headers=HEADERS).status_code == 200
        first = client.post(endpoint, json={}, headers=HEADERS)
        assert first.status_code == 200 and first.json()["rules_count"] == expected_rules
        answered = client.post(endpoint, json={"answer": "Synthetic club runs design workshops."}, headers=HEADERS)
        assert answered.status_code == 200, answered.text
        assert answered.json()["index"] == 2
        pending = client.get("/api/review").json()
        assert len(pending) == 1 and pending[0]["status"] == "pending"
        assert "design workshops" in pending[0]["statement"]
        assert "design workshops" not in client.get("/api/knowledge?tab=tips").text
        for _ in QUESTIONS[1:]:
            response = client.post(endpoint, json={"answer": "[skip]"}, headers=HEADERS)
        assert response.json()["done"] and SetupService(tmp_path).complete("running-club")
        assert len(adapter.captures) == 1
        client.post("/api/auth/dev", json={"email": "other@example.com"}, headers=HEADERS)
        assert client.post(endpoint, json={}, headers=HEADERS).json()["index"] == 1
        assert client.get("/api/review").json() == []
        assert client.post(endpoint, json={}, headers=HEADERS).json()["rules_count"] == expected_rules


def test_real_sqlite_queue_retry_is_idempotent_after_a_partial_failure(tmp_path: Path) -> None:
    adapter = Adapter(tmp_path)
    adapter.fail_after_queue = True
    with TestClient(setup_app(tmp_path, adapter)) as client:
        client.post("/api/auth/dev", json={"email": "president@example.com"}, headers=HEADERS)
        response = client.post("/api/setup/next", json={"answer": "Synthetic answer"}, headers=HEADERS)
        assert response.status_code == 503
        assert len(client.get("/api/review").json()) == 1
        resumed = client.post("/api/setup/next", json={}, headers=HEADERS)
        assert resumed.status_code == 200 and resumed.json()["index"] == 2
        assert len(client.get("/api/review").json()) == 1 and len(adapter.captures) == 1
        assert "design workshops" not in client.get("/api/knowledge?tab=tips").text
