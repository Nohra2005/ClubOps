from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from clubops.contracts.forms import FormTemplate
from clubops.knowhow.backends import SqliteBackend, open_club_store_backend
from clubops.knowhow.store import KnowHowStore


@pytest.fixture(params=["memory", "sqlite", "split"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[KnowHowStore]:
    """Every store test runs on every backend, so they all follow the same rules."""
    if request.param == "memory":
        made = KnowHowStore()
    elif request.param == "sqlite":
        made = KnowHowStore(SqliteBackend(tmp_path / "club.db"))
    else:
        made = KnowHowStore(open_club_store_backend(tmp_path, "running-club"))
    yield made
    made.close()


@pytest.fixture(scope="session")
def template() -> FormTemplate:
    raw = json.loads(Path("data/forms/osa_event_proposal_2026_2027.json").read_text())
    return FormTemplate.model_validate(raw)
