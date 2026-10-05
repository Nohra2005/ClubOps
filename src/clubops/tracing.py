"""Trace sinks. A trace line holds metadata only (capability, timing, tokens, cost, status),
never request or response content, so personal data cannot leak into traces."""

from __future__ import annotations

import json
from pathlib import Path

from clubops.contracts.common import ErrorCode, Status, TraceMeta


class JsonlTracer:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, trace: TraceMeta, status: Status, error: ErrorCode | None) -> None:
        line = {**trace.model_dump(mode="json"), "status": status.value, "error": error.value if error else None}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")


class MemoryTracer:
    def __init__(self) -> None:
        self.records: list[tuple[TraceMeta, Status, ErrorCode | None]] = []

    def record(self, trace: TraceMeta, status: Status, error: ErrorCode | None) -> None:
        self.records.append((trace, status, error))
