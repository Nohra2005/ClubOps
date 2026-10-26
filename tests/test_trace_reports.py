"""C-20: per-feature cost/tokens/timing/retries/failures from published trace metadata."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from clubops.contracts.common import ErrorCode, Status, TraceMeta
from clubops.reports.traces import record_trace, summarize_traces, trace_path


def trace(trace_id: str = "trace-example", capability: str = "ask") -> TraceMeta:
    return TraceMeta(
        trace_id=trace_id,
        capability=capability,
        capability_version="0.2.0",
        started_at=datetime(2026, 10, 26, tzinfo=UTC),
        latency_ms=200,
        tokens_in=100,
        tokens_out=20,
        cost_usd=Decimal("0.003"),
        retries=1,
    )


def test_trace_metrics_are_deduplicated_and_separated_by_feature_and_club(tmp_path: Path) -> None:
    first = trace()
    for _ in range(2):
        record_trace(tmp_path, "running-club", first, Status.OK, None)
    record_trace(tmp_path, "running-club", trace("trace-failed"), Status.FAILED, ErrorCode.UPSTREAM_ERROR)
    record_trace(tmp_path, "running-club", trace("trace-draft", "draft"), Status.OK, None)
    rows = summarize_traces(trace_path(tmp_path, "running-club"), "2026-10")
    assert rows[0] == {
        "name": "ask",
        "calls": 2,
        "tokens_in": 200,
        "tokens_out": 40,
        "latency_ms": 400,
        "retries": 2,
        "failures": 1,
        "cost_usd": 0.006,
    }
    assert rows[1]["name"] == "draft" and rows[1]["calls"] == 1
    assert summarize_traces(trace_path(tmp_path, "asme"), "2026-10") == []
    assert summarize_traces(trace_path(tmp_path, "running-club"), "2026-11") == []


def test_private_payloads_and_broken_metadata_fail_without_echoing_content(tmp_path: Path) -> None:
    path = tmp_path / "traces.jsonl"
    value = trace().model_dump(mode="json") | {"status": "ok", "error": None, "prompt": "PRIVATE CLUB TEXT"}
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid trace metadata") as failure:
        summarize_traces(path, "2026-10")
    assert "PRIVATE CLUB TEXT" not in str(failure.value)
