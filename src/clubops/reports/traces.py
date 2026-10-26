"""Aggregate the published JsonlTracer format; never include raw input or exception diagnostics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from clubops.contracts.common import ErrorCode, Status, TraceMeta
from clubops.reports.runs import _LOCK, BEIRUT, run_path


def trace_path(data_dir: Path, club_id: str) -> Path:
    return run_path(data_dir, club_id).with_name("traces.jsonl")


def record_trace(data_dir: Path, club_id: str, trace: TraceMeta, status: Status, error: ErrorCode | None) -> None:
    """Backend features can use this sink when their club identity is known."""
    path = trace_path(data_dir, club_id)
    value = trace.model_dump(mode="json") | {"status": status.value, "error": error.value if error else None}
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(value) + "\n")


@dataclass
class _Totals:
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    retries: int = 0
    failures: int = 0
    cost: Decimal = Decimal(0)


def summarize_traces(path: Path, month: str) -> list[dict[str, str | int | float]]:
    if not path.exists():
        return []
    traces: dict[str, tuple[TraceMeta, Status]] = {}
    with _LOCK, path.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("not metadata")
                status = Status(value.pop("status"))
                error = value.pop("error", None)
                if error is not None:
                    ErrorCode(error)
                trace = TraceMeta.model_validate(value)
                if trace.started_at.tzinfo is None:
                    raise ValueError("naive time")
            except (ValidationError, ValueError, TypeError, KeyError):
                raise ValueError(f"Invalid trace metadata at line {number}; report not generated.") from None
            traces[trace.trace_id] = trace, status
    groups: dict[str, _Totals] = {}
    for trace, status in traces.values():
        if trace.started_at.astimezone(BEIRUT).strftime("%Y-%m") != month:
            continue
        total = groups.setdefault(trace.capability, _Totals())
        total.calls += 1
        total.tokens_in += trace.tokens_in
        total.tokens_out += trace.tokens_out
        total.latency_ms += trace.latency_ms
        total.retries += trace.retries
        total.failures += status is Status.FAILED
        total.cost += trace.cost_usd
    return [
        {
            "name": name,
            "calls": total.calls,
            "tokens_in": total.tokens_in,
            "tokens_out": total.tokens_out,
            "latency_ms": total.latency_ms,
            "retries": total.retries,
            "failures": total.failures,
            "cost_usd": float(total.cost),
        }
        for name, total in sorted(groups.items())
    ]
