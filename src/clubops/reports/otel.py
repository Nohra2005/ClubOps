"""Opt-in OTLP/HTTP JSON delivery. One bounded attempt, no collector diagnostics.

This is a closed-run batch exporter, not automatic application instrumentation.
The producer must handle the result without changing the planner's outcome.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

import httpx

from clubops.reports.otel_input import RunObservation
from clubops.reports.otel_payload import DEFAULT_LABELS, ExportBatch, PublicLabels, build_batch

ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
MAX_RESPONSE_BYTES = 65_536
Outcome = Literal[
    "disabled",
    "invalid_observation",
    "invalid_endpoint",
    "accepted",
    "partial",
    "warning",
    "http_error",
    "transport_error",
    "invalid_response",
]


@dataclass(frozen=True)
class ExportResult:
    outcome: Outcome
    trace_id: str | None = None
    span_count: int = 0
    rejected_spans: int = 0
    retryable: bool = False


def _endpoint_valid(endpoint: str) -> bool:
    try:
        value = urlsplit(endpoint)
        if len(endpoint) > 4096 or any(c.isspace() or ord(c) < 32 for c in endpoint):
            return False
        if value.username is not None or value.password is not None or value.query or value.fragment:
            return False
        if not value.hostname or value.port == 0:
            return False
        return value.scheme == "https" or (
            value.scheme == "http" and value.hostname in {"localhost", "127.0.0.1", "::1"}
        )
    except ValueError:
        return False


def _success(body: bytes, batch: ExportBatch) -> ExportResult:
    try:
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError
        if "partialSuccess" not in value:
            return ExportResult("accepted", batch.trace_id, batch.span_count)
        partial = value["partialSuccess"]
        if not isinstance(partial, dict):
            raise ValueError
        count = partial.get("rejectedSpans", 0)
        if isinstance(count, bool) or not isinstance(count, (str, int)) or not str(count).isascii():
            raise ValueError
        if not str(count).isdigit() or not 0 <= int(count) <= batch.span_count:
            raise ValueError
        rejected = int(count)
        message = partial.get("errorMessage", "")
        if not isinstance(message, str):
            raise ValueError
        # Some collectors serialize an empty default message. It has no rejection
        # or warning; do not turn that into a false delivery failure.
        outcome: Outcome = "partial" if rejected else ("warning" if message else "accepted")
        return ExportResult(outcome, batch.trace_id, batch.span_count, rejected)
    except (ValueError, TypeError):
        return ExportResult("invalid_response", batch.trace_id, batch.span_count)


def export_run(
    observation: RunObservation,
    *,
    endpoint: str | None = None,
    labels: PublicLabels = DEFAULT_LABELS,
    _transport: httpx.BaseTransport | None = None,
) -> ExportResult:
    """Explicit call only; empty endpoint disables even when the environment is set.

    Only the trace-specific environment variable is supported. No global SDK,
    process environment, headers, .env, prompts or existing trace files are read.
    Endpoint and label configuration must come from trusted server configuration.
    """
    target = os.environ.get(ENDPOINT_ENV, "") if endpoint is None else endpoint
    if not target:
        return ExportResult("disabled")
    if not _endpoint_valid(target):
        return ExportResult("invalid_endpoint")
    try:
        batch = build_batch(observation, labels)
    except (ValueError, TypeError, OverflowError):
        return ExportResult("invalid_observation")
    try:
        with (
            httpx.Client(timeout=3.0, follow_redirects=False, trust_env=False, transport=_transport) as client,
            client.stream(
                "POST",
                target,
                content=batch.body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
            ) as response,
        ):
            if response.status_code != 200:
                return ExportResult(
                    "http_error",
                    batch.trace_id,
                    batch.span_count,
                    retryable=response.status_code in {429, 502, 503, 504},
                )
            if response.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
                return ExportResult("invalid_response", batch.trace_id, batch.span_count)
            body = bytearray()
            for chunk in response.iter_bytes(chunk_size=8192):
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    return ExportResult("invalid_response", batch.trace_id, batch.span_count)
            return _success(bytes(body), batch)
    except httpx.HTTPError:
        return ExportResult("transport_error", batch.trace_id, batch.span_count, retryable=True)
