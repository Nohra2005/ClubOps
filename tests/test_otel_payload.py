import json
import re
from dataclasses import replace

import pytest

from clubops.contracts.agent import RunStatus
from clubops.contracts.common import ErrorCode, Status
from clubops.reports.otel_payload import PublicLabels, build_batch
from tests.otel_fixtures import observation

LABELS = PublicLabels(
    tools=frozenset({"search-memory"}),
    capabilities=frozenset({"planner"}),
    capability_versions=frozenset({"1.0.0"}),
    prompt_versions=frozenset({"planner-v1"}),
    models=frozenset({"synthetic-model"}),
)


def test_otlp_hierarchy_and_metadata() -> None:
    batch = build_batch(observation(), LABELS)
    payload = json.loads(batch.body)
    root, step, call = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert batch.span_count == 3
    assert re.fullmatch("[0-9a-f]{32}", batch.trace_id)
    assert len({s["spanId"] for s in (root, step, call)}) == 3
    for span in (root, step, call):
        assert span["traceId"] == batch.trace_id
        assert re.fullmatch("[0-9a-f]{16}", span["spanId"])
        assert span["startTimeUnixNano"].isdigit() and span["endTimeUnixNano"].isdigit()
        assert span["status"] == {"code": 1}
    assert "parentSpanId" not in root
    assert step["parentSpanId"] == root["spanId"]
    assert call["parentSpanId"] == step["spanId"] and call["kind"] == 3
    assert int(call["endTimeUnixNano"]) - int(call["startTimeUnixNano"]) == 200_000_000
    attrs = {a["key"]: a["value"] for a in call["attributes"]}
    assert attrs["clubops.call.tokens_in"] == {"intValue": "100"}
    assert attrs["clubops.call.replayed"] == {"boolValue": True}
    assert attrs["clubops.call.cost_usd"] == {"stringValue": "0.003"}
    assert attrs["clubops.call.prompt_version"] == {"stringValue": "planner-v1"}


def test_private_fields_and_unregistered_labels_never_exported() -> None:
    value = observation()
    step = value.run.steps[0].model_copy(
        update={"text": "Synthetic Person canary@example.invalid", "tool": "private-tool"}
    )
    run = value.run.model_copy(
        update={"club_id": "private-club", "run_id": "private-run", "event_id": "ev-private-event", "steps": [step]}
    )
    call = value.calls[0]
    trace = call.trace.model_copy(
        update={
            "trace_id": "private-trace",
            "capability": "private-capability",
            "capability_version": "123.456.789",
            "model": "canary@example.invalid",
            "prompt_version": "Synthetic Person prompt",
        }
    )
    call = replace(call, club_id=run.club_id, run_id=run.run_id, trace=trace)
    batch = build_batch(replace(value, run=run, calls=(call,)), LABELS)
    body = batch.body.decode()
    for marker in ("private", "Synthetic Person", "canary@", "123.456.789"):
        assert marker not in body
    assert "unregistered" in body
    assert "Synthetic Person" not in repr(batch)
    assert "Synthetic Person" not in repr(value)


def test_default_policy_suppresses_all_labels_and_new_exports_have_new_ids() -> None:
    one, two = build_batch(observation()), build_batch(observation())
    assert one.trace_id != two.trace_id
    assert "planner" not in one.body.decode()
    assert "synthetic-model" not in one.body.decode()


def test_failed_spans_use_only_enumerated_error() -> None:
    value = observation()
    run = value.run.model_copy(update={"status": RunStatus.FAILED})
    call = replace(value.calls[0], status=Status.FAILED, error=ErrorCode.UPSTREAM_TIMEOUT)
    payload = json.loads(build_batch(replace(value, run=run, calls=(call,))).body)
    spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert spans[0]["status"] == spans[2]["status"] == {"code": 2}
    assert {"key": "clubops.call.error_code", "value": {"stringValue": "upstream_timeout"}} in spans[2]["attributes"]


def test_otlp_integer_overflow_rejected() -> None:
    value = observation()
    call = value.calls[0]
    call = replace(call, trace=call.trace.model_copy(update={"tokens_in": 2**63}))
    with pytest.raises(ValueError, match="Invalid telemetry observation"):
        build_batch(replace(value, calls=(call,)))
