"""Frozen synthetic attacks and honest outcome scoring for J-13."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.security.score_attacks import BENIGN, CORPUS, benign_ids, case_ids, score_outcomes

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


def test_benign_source_text_is_not_an_injection() -> None:
    assert len(benign_ids()) == 4
    cases = json.loads(BENIGN.read_text(encoding="utf-8"))["cases"]
    assert all(not injection_flags(case["text"]) for case in cases)


def sample_outcomes() -> dict[str, list[dict[str, object]]]:
    attacks = [
        {"mode": mode, "case_id": case_id, "succeeded": mode == "defense_off" and case_id == "A01"}
        for mode in ("defense_off", "defense_on")
        for case_id in sorted(case_ids())
    ]
    benign = [
        {"mode": mode, "case_id": case_id, "falsely_flagged": mode == "defense_on" and case_id == "B01"}
        for mode in ("defense_off", "defense_on")
        for case_id in sorted(benign_ids())
    ]
    return {"outcomes": attacks, "benign_outcomes": benign}


def test_scoring_requires_complete_independent_outcomes(tmp_path: Path) -> None:
    data = sample_outcomes()
    path = tmp_path / "outcomes.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert score_outcomes(path, case_ids(), benign_ids()) == {
        "defense_off": (1, 10, 0, 4),
        "defense_on": (0, 10, 1, 4),
    }

    path.write_text(json.dumps({**data, "outcomes": data["outcomes"][:-1]}), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        score_outcomes(path, case_ids(), benign_ids())

    path.write_text(json.dumps({**data, "benign_outcomes": data["benign_outcomes"][:-1]}), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        score_outcomes(path, case_ids(), benign_ids())

    path.write_text(json.dumps({**data, "outcomes": [*data["outcomes"], data["outcomes"][0]]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        score_outcomes(path, case_ids(), benign_ids())


def test_scoring_rejects_private_text_and_non_boolean_results(tmp_path: Path) -> None:
    data = sample_outcomes()
    path = tmp_path / "outcomes.json"
    for bad in (
        {"mode": "defense_on", "case_id": "A01", "succeeded": False, "response": "private"},
        {"mode": "defense_on", "case_id": "A01", "succeeded": "false"},
        {"mode": "defense_on", "case_id": "B01", "falsely_flagged": "false"},
    ):
        key = "benign_outcomes" if bad["case_id"] == "B01" else "outcomes"
        path.write_text(json.dumps({**data, key: [bad]}), encoding="utf-8")
        with pytest.raises(ValueError, match=r"invalid|private|extra"):
            score_outcomes(path, case_ids(), benign_ids())


def test_changed_corpus_is_rejected_before_scoring(tmp_path: Path) -> None:
    path = tmp_path / "attack-corpus.json"
    path.write_bytes(CORPUS.read_bytes() + b" ")
    with pytest.raises(ValueError, match="frozen"):
        case_ids(path)
    path.write_bytes(BENIGN.read_bytes() + b" ")
    with pytest.raises(ValueError, match="frozen"):
        benign_ids(path)
