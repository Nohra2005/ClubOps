"""Synthetic setup data; extraction/queue callbacks are the published boundary."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from clubops.api.setup import QUESTIONS, SetupConflict, SetupService, SetupStep, router
from clubops.contracts.common import Actor, Role
from clubops.contracts.knowhow import CaptureRequest, CaptureResult, KnowHowProposal
from tests.factories import NOW, actor, item, proposal, rule


class Backend:
    def __init__(self) -> None:
        self.inputs: list[CaptureRequest] = []
        self.queued: dict[str, KnowHowProposal] = {}
        self.fail_queue = False

    def capture(self, request: CaptureRequest) -> CaptureResult:
        self.inputs.append(request)
        candidate = item(club_id=request.club_id, statement=request.sources[0].content)
        return CaptureResult(
            proposals=[proposal(candidate, pid=f"setup-test-{len(self.inputs)}")], sources_seen=1, sources_skipped=0
        )

    def submit(self, value: KnowHowProposal) -> None:
        self.queued[value.proposal_id] = value
        if self.fail_queue:
            raise RuntimeError("synthetic secret must not reach an HTTP error")


def advance(
    service: SetupService,
    backend: Backend,
    answer: str | None = None,
    user: Actor | None = None,
    now: datetime = NOW,
) -> SetupStep:
    return service.next(
        user or actor(), answer, now=now, rules_count=25, capture=backend.capture, submit=backend.submit
    )


def test_resume_skip_restart_and_complete_without_approving(tmp_path: Path) -> None:
    service, backend = SetupService(tmp_path), Backend()
    assert not service.complete("running-club")
    assert advance(service, backend).index == 1
    assert advance(service, backend).index == 1 and not backend.inputs
    first = advance(service, backend, "Synthetic club")
    assert first.index == 2 and not first.done and first.rules_count == 25
    assert len(backend.queued) == 1
    queued = next(iter(backend.queued.values()))
    assert queued.candidate.status.value == "proposed" and queued.candidate.verified_by is None
    request = backend.inputs[0]
    assert request.club_id == "running-club"
    assert request.sources[0].source.kind.value == "interview"
    assert "Synthetic club" in request.sources[0].content
    assert request.sources[0].source.locator == "Club setup question 1"
    restarted = SetupService(tmp_path)
    assert advance(restarted, backend).index == 2
    for _ in QUESTIONS[1:]:
        result = advance(restarted, backend, "[skip]")
    assert result.done and result.index == 10 and restarted.complete("running-club")
    assert len(backend.inputs) == 1
    with pytest.raises(SetupConflict, match="already complete"):
        advance(restarted, backend, "late duplicate")
    assert advance(restarted, backend).done
    # Progress doesn't retain a duplicate raw answer once it reached Review.
    with closing(sqlite3.connect(tmp_path / "setup/running-club.sqlite3")) as connection:
        assert connection.execute("SELECT digest, pending FROM progress").fetchone() == (None, None)


def test_club_progress_is_isolated_and_ids_cannot_escape_the_directory(tmp_path: Path) -> None:
    service, backend = SetupService(tmp_path), Backend()
    advance(service, backend, "Synthetic Running Club")
    assert advance(service, backend, user=actor(club="asme")).index == 1
    with pytest.raises(ValidationError):
        service.complete("../outside")


def test_an_empty_initializing_file_is_incomplete_not_a_server_error(tmp_path: Path) -> None:
    (tmp_path / "setup").mkdir()
    (tmp_path / "setup/running-club.sqlite3").touch()
    service, backend = SetupService(tmp_path), Backend()
    assert not service.complete("running-club")
    assert advance(service, backend).index == 1


@pytest.mark.parametrize("user", [actor(Role.EVENTS), actor(Role.ADVISER), actor(verified=False)])
def test_only_an_authenticated_president_can_change_setup(tmp_path: Path, user: Actor) -> None:
    service, backend = SetupService(tmp_path), Backend()
    with pytest.raises(PermissionError):
        advance(service, backend, "Synthetic answer", user)
    assert not backend.inputs and not (tmp_path / "setup").exists()


@pytest.mark.parametrize("answer", ["", "  ", "x" * 2001])
def test_bad_answers_leave_the_question_unchanged(tmp_path: Path, answer: str) -> None:
    service, backend = SetupService(tmp_path), Backend()
    with pytest.raises(ValidationError):
        advance(service, backend, answer)
    assert advance(service, backend).index == 1 and not backend.inputs


@pytest.mark.parametrize(
    "bad",
    [proposal(item(club_id="asme")), proposal(rule()), proposal(item(verified_by="m-synthetic", verified_at=NOW))],
)
def test_extraction_cannot_queue_other_clubs_rules_or_verified_memory(tmp_path: Path, bad: KnowHowProposal) -> None:
    service, backend = SetupService(tmp_path), Backend()

    def capture(_: CaptureRequest) -> CaptureResult:
        return CaptureResult(proposals=[bad], sources_seen=1, sources_skipped=0)

    with pytest.raises(ValueError, match="unapproved facts"):
        service.next(actor(), "Synthetic answer", now=NOW, rules_count=0, capture=capture, submit=backend.submit)
    assert not backend.queued and advance(service, backend).index == 1


def test_failed_partial_queue_retries_exact_proposals_without_another_model_call(tmp_path: Path) -> None:
    backend = Backend()
    backend.fail_queue = True
    with pytest.raises(RuntimeError):
        advance(SetupService(tmp_path), backend, "Synthetic answer")
    assert len(backend.inputs) == len(backend.queued) == 1
    backend.fail_queue = False
    with pytest.raises(SetupConflict, match="previous answer"):
        advance(SetupService(tmp_path), backend, "Another answer")
    result = advance(SetupService(tmp_path), backend)  # explicit Resume click
    assert result.index == 2
    assert len(backend.inputs) == len(backend.queued) == 1


def test_extraction_failure_does_not_advance_or_persist_the_answer(tmp_path: Path) -> None:
    service, backend = SetupService(tmp_path), Backend()

    def fail(_: CaptureRequest) -> CaptureResult:
        raise RuntimeError("synthetic model failure")

    with pytest.raises(RuntimeError):
        service.next(actor(), "Synthetic answer", now=NOW, rules_count=25, capture=fail, submit=backend.submit)
    assert advance(service, backend).index == 1 and not backend.queued


def test_router_enforces_auth_csrf_validation_and_sanitizes_errors(tmp_path: Path) -> None:
    backend, service = Backend(), SetupService(tmp_path)

    def signed_in(request: Request) -> Actor:
        role = request.headers.get("Test-Role")
        if not role:
            raise HTTPException(401, "Sign in.")
        return actor(Role(role))

    app = FastAPI()
    app.include_router(
        router(
            service,
            actor_dependency=signed_in,
            capture=backend.capture,
            submit=backend.submit,
            rules_count=lambda club, on: 25,
            clock=lambda: NOW,
        )
    )
    with TestClient(app) as client:
        endpoint = "/api/setup/next"
        assert client.post(endpoint, json={}).status_code == 401
        headers = {"Test-Role": "president", "X-Requested-With": "ClubOps"}
        assert client.post(endpoint, json={}, headers={"Test-Role": "president"}).status_code == 403
        assert client.post(endpoint, json={}, headers={**headers, "Test-Role": "adviser"}).status_code == 403
        assert client.post(endpoint, json={"club_id": "asme"}, headers=headers).status_code == 422
        assert client.post(endpoint, json={"answer": " "}, headers=headers).status_code == 422
        assert client.post(endpoint, json={}, headers=headers).json()["index"] == 1
        backend.fail_queue = True
        response = client.post(endpoint, json={"answer": "Synthetic input"}, headers=headers)
        assert response.status_code == 503 and "synthetic secret" not in response.text
        backend.fail_queue = False
        assert client.post(endpoint, json={"answer": "Different"}, headers=headers).status_code == 409
        assert client.post(endpoint, json={}, headers=headers).json()["index"] == 2
