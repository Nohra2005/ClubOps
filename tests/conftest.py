from __future__ import annotations

import json
from pathlib import Path

import pytest

from clubops.contracts.forms import FormTemplate
from clubops.knowhow.store import KnowHowStore


@pytest.fixture
def store() -> KnowHowStore:
    return KnowHowStore()


@pytest.fixture(scope="session")
def template() -> FormTemplate:
    raw = json.loads(Path("data/forms/osa_event_proposal_2026_2027.json").read_text())
    return FormTemplate.model_validate(raw)
