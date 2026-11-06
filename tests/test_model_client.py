"""The model client: replay/record/live, validation, cost, budget and provider errors.

Everything runs against a fake provider (httpx.MockTransport) with synthetic content:
no network, no API key, no cost.
"""

from __future__ import annotations

import dataclasses
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from clubops.capabilities.runner import CapabilityError
from clubops.config import ModelMode, Settings
from clubops.contracts.common import ErrorCode
from clubops.model import Budget, ModelClient, ModelRequest


class Verdict(BaseModel):
    applies: bool
    reason: str


REQUEST = ModelRequest(prompt_version="test-1", system="Answer in JSON.", user="Does rule R apply to event E?")
GOOD = json.dumps({"applies": True, "reason": "event has outside guests"})


def settings(tmp_path: Path, mode: ModelMode, **over: object) -> Settings:
    values: dict[str, object] = {
        "base_url": "https://provider.test/v1",
        "api_key": SecretStr("sk-test-secret"),
        "model": "fake-model",
        "price_in_per_mtok": Decimal("1.00"),
        "price_out_per_mtok": Decimal("2.00"),
        "budget_usd_per_packet": Decimal("0.05"),
        "max_steps_per_plan": 8,
        "mode": mode,
        "recordings_dir": tmp_path / "recordings",
        "trace_path": tmp_path / "trace.jsonl",
    }
    values.update(over)
    return Settings(**values)  # type: ignore[arg-type]


def provider(
    content: str = GOOD, status: int = 200, tokens: tuple[int, int] = (1000, 500)
) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if status != 200:
            return httpx.Response(status, json={"error": "nope"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": tokens[0], "completion_tokens": tokens[1]},
            },
        )

    return httpx.MockTransport(handle), seen


# ----------------------------------------------------------------- modes


def test_record_then_replay_gives_the_same_answer_without_network(tmp_path: Path) -> None:
    transport, seen = provider()
    answer, usage = ModelClient(settings(tmp_path, ModelMode.RECORD), transport=transport).complete(REQUEST, Verdict)
    assert answer == Verdict(applies=True, reason="event has outside guests")
    assert len(seen) == 1
    assert usage.cost_usd == Decimal("0.002")  # 1000 * $1/M + 500 * $2/M

    never, never_seen = provider(status=500)
    replayed, replay_usage = ModelClient(settings(tmp_path, ModelMode.REPLAY), transport=never).complete(
        REQUEST, Verdict
    )
    assert replayed == answer
    assert never_seen == []
    assert replay_usage.replayed is True
    assert replay_usage.cost_usd == Decimal("0")


def test_replay_without_a_recording_fails_and_never_calls_the_provider(tmp_path: Path) -> None:
    transport, seen = provider()
    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.REPLAY), transport=transport).complete(REQUEST, Verdict)
    assert exc.value.code is ErrorCode.NOT_FOUND
    assert seen == []


def test_live_mode_saves_nothing(tmp_path: Path) -> None:
    transport, _ = provider()
    ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport).complete(REQUEST, Verdict)
    assert not (tmp_path / "recordings").exists()


def test_a_changed_prompt_needs_a_new_recording(tmp_path: Path) -> None:
    transport, _ = provider()
    ModelClient(settings(tmp_path, ModelMode.RECORD), transport=transport).complete(REQUEST, Verdict)
    changed = ModelRequest(prompt_version="test-2", system=REQUEST.system, user=REQUEST.user)
    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.REPLAY)).complete(changed, Verdict)
    assert exc.value.code is ErrorCode.NOT_FOUND


def test_recordings_never_contain_the_api_key_or_the_prompt(tmp_path: Path) -> None:
    transport, seen = provider()
    ModelClient(settings(tmp_path, ModelMode.RECORD), transport=transport).complete(REQUEST, Verdict)
    saved = "".join(p.read_text() for p in (tmp_path / "recordings").rglob("*.json"))
    assert "sk-test-secret" not in saved
    assert REQUEST.user not in saved
    assert seen[0].headers["Authorization"] == "Bearer sk-test-secret"


# ------------------------------------------------------------ validation


def test_answer_in_a_code_fence_is_accepted(tmp_path: Path) -> None:
    transport, _ = provider(content=f"```json\n{GOOD}\n```")
    answer, _ = ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport).complete(REQUEST, Verdict)
    assert answer.applies is True


@pytest.mark.parametrize("content", ["not json at all", json.dumps({"applies": "maybe"})])
def test_malformed_answer_is_retryable_and_its_cost_is_counted(tmp_path: Path, content: str) -> None:
    transport, _ = provider(content=content)
    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.RECORD), transport=transport).complete(REQUEST, Verdict)
    assert exc.value.code is ErrorCode.MALFORMED_MODEL_OUTPUT
    assert exc.value.usage.cost_usd == Decimal("0.002")
    assert not (tmp_path / "recordings").exists()  # bad answers are never saved for replay


# ---------------------------------------------------------------- errors


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (429, ErrorCode.RATE_LIMITED),
        (500, ErrorCode.UPSTREAM_ERROR),
        (503, ErrorCode.UPSTREAM_ERROR),
        (401, ErrorCode.INTERNAL),
    ],
)
def test_provider_errors_map_to_shared_error_codes(tmp_path: Path, status: int, code: ErrorCode) -> None:
    transport, _ = provider(status=status)
    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport).complete(REQUEST, Verdict)
    assert exc.value.code is code
    assert "sk-test-secret" not in exc.value.message


def test_provider_timeout_is_an_upstream_timeout(tmp_path: Path) -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.LIVE), transport=httpx.MockTransport(slow)).complete(REQUEST, Verdict)
    assert exc.value.code is ErrorCode.UPSTREAM_TIMEOUT


def test_unreachable_provider_is_an_upstream_error(tmp_path: Path) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.LIVE), transport=httpx.MockTransport(down)).complete(REQUEST, Verdict)
    assert exc.value.code is ErrorCode.UPSTREAM_ERROR


def test_unexpected_response_shape_is_an_upstream_error(tmp_path: Path) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []}))
    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport).complete(REQUEST, Verdict)
    assert exc.value.code is ErrorCode.UPSTREAM_ERROR


def test_missing_configuration_fails_clearly_without_calling(tmp_path: Path) -> None:
    transport, seen = provider()
    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.LIVE, api_key=None), transport=transport).complete(REQUEST, Verdict)
    assert exc.value.code is ErrorCode.INTERNAL
    assert seen == []


# ---------------------------------------------------------------- budget


def test_step_limit_stops_the_next_call_before_it_is_paid(tmp_path: Path) -> None:
    transport, seen = provider()
    client = ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport)
    budget = Budget(max_usd=Decimal("1"), max_steps=2)
    client.complete(REQUEST, Verdict, budget)
    client.complete(REQUEST, Verdict, budget)
    with pytest.raises(CapabilityError) as exc:
        client.complete(REQUEST, Verdict, budget)
    assert exc.value.code is ErrorCode.BUDGET_EXCEEDED
    assert len(seen) == 2


def test_cost_limit_stops_the_next_call(tmp_path: Path) -> None:
    transport, seen = provider(tokens=(20_000, 10_000))  # $0.04 per call
    client = ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport)
    budget = settings(tmp_path, ModelMode.LIVE).new_budget()  # $0.05, 8 steps
    client.complete(REQUEST, Verdict, budget)
    client.complete(REQUEST, Verdict, budget)  # allowed: only $0.04 spent before it
    with pytest.raises(CapabilityError) as exc:
        client.complete(REQUEST, Verdict, budget)
    assert exc.value.code is ErrorCode.BUDGET_EXCEEDED
    assert len(seen) == 2
    assert budget.spent_usd == Decimal("0.08")
    assert budget.remaining_usd == Decimal("0")


def test_replayed_calls_still_count_as_steps(tmp_path: Path) -> None:
    transport, _ = provider()
    ModelClient(settings(tmp_path, ModelMode.RECORD), transport=transport).complete(REQUEST, Verdict)
    client = ModelClient(settings(tmp_path, ModelMode.REPLAY))
    budget = Budget(max_usd=Decimal("1"), max_steps=1)
    client.complete(REQUEST, Verdict, budget)
    with pytest.raises(CapabilityError) as exc:
        client.complete(REQUEST, Verdict, budget)
    assert exc.value.code is ErrorCode.BUDGET_EXCEEDED


def test_openrouter_requests_ask_for_providers_that_do_not_keep_prompts(tmp_path: Path) -> None:
    transport, seen = provider()
    s = settings(tmp_path, ModelMode.LIVE, base_url="https://openrouter.ai/api/v1")
    ModelClient(s, transport=transport).complete(REQUEST, Verdict)
    assert json.loads(seen[0].content)["provider"] == {"data_collection": "deny"}

    other, other_seen = provider()
    ModelClient(settings(tmp_path, ModelMode.LIVE), transport=other).complete(REQUEST, Verdict)
    assert "provider" not in json.loads(other_seen[0].content)


def test_the_provider_is_given_the_exact_answer_shape(tmp_path: Path) -> None:
    transport, seen = provider()
    ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport).complete(REQUEST, Verdict)
    rf = json.loads(seen[0].content)["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["name"] == "Verdict"
    assert set(rf["json_schema"]["schema"]["properties"]) == {"applies", "reason"}


def test_a_wrong_shape_says_which_field_was_wrong(tmp_path: Path) -> None:
    transport, _ = provider(content=json.dumps({"applies": "maybe", "reason": "x"}))
    with pytest.raises(CapabilityError) as exc:
        ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport).complete(REQUEST, Verdict)
    assert exc.value.code is ErrorCode.MALFORMED_MODEL_OUTPUT
    assert "applies" in exc.value.message


def test_thinking_models_are_asked_to_think_briefly_unless_turned_off(tmp_path: Path) -> None:
    transport, seen = provider()
    ModelClient(settings(tmp_path, ModelMode.LIVE), transport=transport).complete(REQUEST, Verdict)
    assert json.loads(seen[0].content)["reasoning"] == {"effort": "low"}

    off, off_seen = provider()
    ModelClient(settings(tmp_path, ModelMode.LIVE, reasoning_effort=None), transport=off).complete(REQUEST, Verdict)
    assert "reasoning" not in json.loads(off_seen[0].content)


def test_answer_schemas_are_simplified_for_providers() -> None:
    from clubops.model.client import provider_schema

    raw = {
        "type": "object",
        "properties": {
            "a": {"anyOf": [{"type": "string", "maxLength": 5}, {"type": "null"}], "default": None},
            "b": {"oneOf": [{"type": "integer"}, {"type": "string"}], "discriminator": {"propertyName": "k"}},
            "c": {"type": "array", "items": {"type": "string", "pattern": "^x$"}, "maxItems": 20},
        },
    }
    assert provider_schema(raw) == {
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
            "c": {"type": "array", "items": {"type": "string"}},
        },
    }


def test_a_refused_schema_is_retried_as_plain_json_with_the_shape_in_the_instructions(tmp_path: Path) -> None:
    seen: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if body["response_format"]["type"] == "json_schema":
            return httpx.Response(400, json={"error": {"message": "The compiled grammar is too large"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": GOOD}}], "usage": {}})

    client = ModelClient(settings(tmp_path, ModelMode.LIVE), transport=httpx.MockTransport(handle))
    answer, _ = client.complete(REQUEST, Verdict)
    assert answer.applies is not None
    assert [b["response_format"]["type"] for b in seen] == ["json_schema", "json_object"]
    assert "Answer JSON matching this schema" in seen[1]["messages"][0]["content"]

    seen.clear()
    client.complete(dataclasses.replace(REQUEST, schema_in_prompt=True, prompt_version="v-direct"), Verdict)
    assert [b["response_format"]["type"] for b in seen] == ["json_object"]  # no request that is refused first
