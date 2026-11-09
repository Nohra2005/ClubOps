"""Opt-in debug log: one JSON line per model attempt, model error and evaluation case.

Switched on by CLUBOPS_DEBUG_LOG=<path>. Off by default, so normal runs write nothing. It never stores the
API key or the request. It does store the start of provider error bodies and of malformed model answers, which
may contain club text: keep the file under data/private/ (never committed). Writing can never break a run.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def log(kind: str, **fields: Any) -> None:
    path = os.environ.get("CLUBOPS_DEBUG_LOG")
    if not path:
        return
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        line = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"), "kind": kind, **fields}
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, default=str, ensure_ascii=False) + "\n")
    except (OSError, TypeError, ValueError):
        pass
