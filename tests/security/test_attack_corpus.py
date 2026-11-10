"""Frozen synthetic attacks and honest outcome scoring for J-13."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.security.score_attacks import CORPUS, case_ids, score_outcomes

from clubops.learning.capture import injection_flags


def test_frozen_cases_cover_untrusted_surfaces_and_trigger_review_flags() -> None:
    ids = case_ids()
    cases = json.loads(CORPUS.read_text(encoding="utf-8"))["cases"]
    assert len(ids) == 10
    assert {case["surface"] for case in cases} == {
        "event_description",
        "forwarded_email",
        "document",
        "chat",
        "after_event_form",
    }
    assert all(injection_flags(case["text"]) for case in cases)


def test_scoring_requires_complete_independent_outcomes(tmp_path: Path) -> None:
    ids = case_ids()
    outcomes = [
        {"mode": mode, "case_id": case_id, "succeeded": mode == "defense_off" and case_id == "A01"}
        for mode in ("defense_off", "defense_on")
        for case_id in sorted(ids)
    ]
    path = tmp_path / "outcomes.json"
    path.write_text(json.dumps({"outcomes": outcomes}), encoding="utf-8")
    assert score_outcomes(path, ids) == {"defense_off": (1, 10), "defense_on": (0, 10)}

    path.write_text(json.dumps({"outcomes": outcomes[:-1]}), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        score_outcomes(path, ids)

    path.write_text(json.dumps({"outcomes": [*outcomes, outcomes[0]]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        score_outcomes(path, ids)


def test_scoring_rejects_private_text_and_non_boolean_results(tmp_path: Path) -> None:
    ids = case_ids()
    path = tmp_path / "outcomes.json"
    for bad in (
        {"mode": "defense_on", "case_id": "A01", "succeeded": False, "response": "private"},
        {"mode": "defense_on", "case_id": "A01", "succeeded": "false"},
    ):
        path.write_text(json.dumps({"outcomes": [bad]}), encoding="utf-8")
        with pytest.raises(ValueError, match=r"invalid|private"):
            score_outcomes(path, ids)


def test_changed_corpus_is_rejected_before_scoring(tmp_path: Path) -> None:
    path = tmp_path / "attack-corpus.json"
    path.write_bytes(CORPUS.read_bytes() + b" ")
    with pytest.raises(ValueError, match="frozen"):
        case_ids(path)
