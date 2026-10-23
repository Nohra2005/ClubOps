"""Saved model answers, so tests and evaluations replay for free and give the same result every time.

A recording is keyed by a hash of everything that shapes the answer (model, prompt version,
messages, output schema). Only the answer text and token counts are stored, never the prompt,
so a recording file holds no more personal data than the answer itself. Recordings of real
club data are never committed (D-04): point ``CLUBOPS_RECORDINGS_DIR`` at a private folder.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Recording:
    key: str
    model: str
    prompt_version: str
    text: str
    tokens_in: int
    tokens_out: int


def recording_key(model: str, prompt_version: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
    """Same inputs -> same key. Any change to the prompt, model or schema makes a new key."""
    canonical = json.dumps(
        {"model": model, "prompt_version": prompt_version, "messages": messages, "schema": schema},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RecordingStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> Recording | None:
        path = self._path(key)
        if not path.is_file():
            return None
        return Recording(**json.loads(path.read_text(encoding="utf-8")))

    def put(self, recording: Recording) -> None:
        path = self._path(recording.key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(recording), ensure_ascii=False, indent=1), encoding="utf-8")
