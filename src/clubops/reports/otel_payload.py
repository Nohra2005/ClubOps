"""Allowlisted projection into OTLP/HTTP JSON. No private text crosses this boundary."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from clubops.reports.otel_input import RunObservation, unix_nanos, validate_observation


@dataclass(frozen=True)
class PublicLabels:
    """Exact public values supplied by trusted code/config, never by request input.

    Defaults deliberately disclose no free-form label. Membership is not a PII
    detector: owners must review configured values before adding them here.
    """

    tools: frozenset[str] = frozenset()
    capabilities: frozenset[str] = frozenset()
    capability_versions: frozenset[str] = frozenset()
    prompt_versions: frozenset[str] = frozenset()
    models: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ExportBatch:
    trace_id: str
    span_count: int
    body: bytes = field(repr=False)


def _label(value: str | None, allowed: frozenset[str]) -> str:
    return value if value in allowed and value is not None else "unregistered"


def _attributes(values: dict[str, str | int | bool]) -> list[dict[str, Any]]:
    result = []
    for key, value in values.items():
        if isinstance(value, bool):
            encoded: dict[str, str | bool] = {"boolValue": value}
        elif isinstance(value, int):
            if not -(2**63) <= value < 2**63:
                raise ValueError("Invalid telemetry observation.")
            encoded = {"intValue": str(value)}
        else:
            encoded = {"stringValue": value}
        result.append({"key": key, "value": encoded})
    return result


DEFAULT_LABELS = PublicLabels()


def build_batch(observation: RunObservation, labels: PublicLabels = DEFAULT_LABELS) -> ExportBatch:
    """One closed run -> one trace; new submission gets new opaque random IDs.

    Reuse the same encoded batch for transport retries, not build_batch again.
    No raw ID, source, event, step text, arbitrary error, prompt or answer is copied.
    """
    value = validate_observation(observation)
    trace_id = secrets.token_hex(16)
    spans: list[dict[str, Any]] = []

    def span(
        name: str,
        start: int,
        end: int,
        status: str,
        attrs: dict[str, str | int | bool],
        *,
        parent: str | None = None,
        kind: int = 1,
    ) -> str:
        span_id = secrets.token_hex(8)
        item: dict[str, Any] = {
            "traceId": trace_id,
            "spanId": span_id,
            "name": name,
            "kind": kind,
            "startTimeUnixNano": str(start),
            "endTimeUnixNano": str(end),
            "attributes": _attributes(attrs),
            "status": {"code": 2 if status == "failed" else 1},
        }
        if parent is not None:
            item["parentSpanId"] = parent
        spans.append(item)
        return span_id

    run = value.run
    root = span(
        "agent.run",
        unix_nanos(value.started_at),
        unix_nanos(value.ended_at),
        run.status.value,
        {
            "clubops.run.status": run.status.value,
            "clubops.run.steps_used": run.steps_used,
            "clubops.run.step_limit": run.step_limit,
            "clubops.run.cost_usd": str(run.cost_usd),
            "clubops.run.cost_limit_usd": str(run.cost_limit_usd),
        },
    )
    windows = {window.n: window for window in value.steps}
    parents: dict[int, str] = {}
    for step in run.steps:
        window = windows[step.n]
        attrs: dict[str, str | int | bool] = {
            "clubops.step.n": step.n,
            "clubops.step.tool": _label(step.tool, labels.tools),
            "clubops.step.state": step.state.value,
        }
        for name, number in (("model_ms", step.model_ms), ("tool_ms", step.tool_ms)):
            if number is not None:
                attrs[f"clubops.step.{name}"] = number
        parents[step.n] = span(
            "agent.step", unix_nanos(window.started_at), unix_nanos(window.ended_at), step.state.value, attrs, parent=root
        )
    for call in value.calls:
        trace = call.trace
        attrs = {
            "clubops.call.capability": _label(trace.capability, labels.capabilities),
            "clubops.call.capability_version": _label(trace.capability_version, labels.capability_versions),
            "clubops.call.prompt_version": _label(trace.prompt_version, labels.prompt_versions),
            "clubops.call.model": _label(trace.model, labels.models),
            "clubops.call.status": call.status.value,
            "clubops.call.latency_ms": trace.latency_ms,
            "clubops.call.tokens_in": trace.tokens_in,
            "clubops.call.tokens_out": trace.tokens_out,
            "clubops.call.cost_usd": str(trace.cost_usd),
            "clubops.call.retries": trace.retries,
            "clubops.call.replayed": trace.replayed,
        }
        if call.error is not None:
            attrs["clubops.call.error_code"] = call.error.value
        span(
            "model.call",
            unix_nanos(trace.started_at),
            unix_nanos(trace.started_at + timedelta(milliseconds=trace.latency_ms)),
            call.status.value,
            attrs,
            parent=parents[call.step_n],
            kind=3,
        )
    payload = {
        "resourceSpans": [
            {
                "resource": {"attributes": _attributes({"service.name": "clubops"})},
                "scopeSpans": [{"scope": {"name": "clubops.reports", "version": "1.0.0"}, "spans": spans}],
            }
        ]
    }
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(body) > 1_048_576:
        raise ValueError("Telemetry batch exceeds size limit.")
    return ExportBatch(trace_id, len(spans), body)
