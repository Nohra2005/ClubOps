"""Central configuration, read from environment variables (and a local ``.env`` if present).

One place for everything that differs between machines or runs: which model provider to call,
what it costs, the spend limit, and whether model calls are live, recorded or replayed.
Nothing here is ever logged or traced; the API key is held as a ``SecretStr``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import SecretStr

if TYPE_CHECKING:
    from clubops.model.budget import Budget


class ModelMode(StrEnum):
    REPLAY = "replay"  # answer only from recordings; never calls the network (default, free, reproducible)
    RECORD = "record"  # call the provider and save each answer for later replay
    LIVE = "live"  # call the provider, save nothing


@dataclass(frozen=True)
class Settings:
    base_url: str | None
    api_key: SecretStr | None
    model: str | None
    price_in_per_mtok: Decimal
    price_out_per_mtok: Decimal
    budget_usd_per_packet: Decimal
    max_steps_per_plan: int
    mode: ModelMode
    recordings_dir: Path
    trace_path: Path

    def new_budget(self) -> Budget:
        """A fresh per-plan budget with the configured limits."""
        from clubops.model.budget import Budget

        return Budget(max_usd=self.budget_usd_per_packet, max_steps=self.max_steps_per_plan)

    @property
    def calls_network(self) -> bool:
        return self.mode is not ModelMode.REPLAY


def _read_dotenv(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE reader. No interpolation, no quotes handling beyond stripping."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def load_settings(env: dict[str, str] | None = None, dotenv: Path = Path(".env")) -> Settings:
    """Environment variables win over ``.env``. Pass ``env`` in tests to avoid touching the real environment."""
    values = {**_read_dotenv(dotenv), **(dict(os.environ) if env is None else env)}

    def get(name: str, default: str | None = None) -> str | None:
        value = values.get(name, default)
        return value or default

    key = get("CLUBOPS_API_KEY")
    return Settings(
        base_url=(get("CLUBOPS_BASE_URL") or "").rstrip("/") or None,
        api_key=SecretStr(key) if key else None,
        model=get("CLUBOPS_MODEL"),
        price_in_per_mtok=Decimal(get("CLUBOPS_PRICE_IN_PER_MTOK", "0") or "0"),
        price_out_per_mtok=Decimal(get("CLUBOPS_PRICE_OUT_PER_MTOK", "0") or "0"),
        budget_usd_per_packet=Decimal(get("CLUBOPS_BUDGET_USD_PER_PACKET", "0.05") or "0.05"),  # D-42
        max_steps_per_plan=int(get("CLUBOPS_MAX_STEPS_PER_PLAN", "8") or "8"),  # D-42
        mode=ModelMode(get("CLUBOPS_MODEL_MODE") or ModelMode.REPLAY.value),
        recordings_dir=Path(get("CLUBOPS_RECORDINGS_DIR", "eval/recordings") or "eval/recordings"),
        trace_path=Path(get("CLUBOPS_TRACE_PATH", "traces/clubops.jsonl") or "traces/clubops.jsonl"),
    )
