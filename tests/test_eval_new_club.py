"""Frozen synthetic starter packs and staged new-club scoring."""

from __future__ import annotations

import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import scripts.eval_new_club as new_club
from scripts.eval_new_club import clubops_predictor, load_packs, run_curve, table

from clubops.config import load_settings
from clubops.evaluation.plans import Prediction, Score
from clubops.model.client import ModelClient


def test_frozen_starters_have_three_isolated_clubs_and_four_stages(tmp_path: Path) -> None:
    packs, cases = load_packs(Path("eval/new-club-starters.json"), Path("eval/synthetic-events.csv"))
    assert {pack.kind for pack in packs} == {"academic", "cultural", "social"}
    assert len({event for pack in packs for event in pack.event_ids}) == 6

    def predictor(pack: object, documents: tuple[object, ...]):
        def predict(case):
            return Prediction(case.truth if documents else frozenset(), cost_usd=Decimal("0.001"))

        return predict

    rows = run_curve(packs, cases, predictor)
    assert len(rows) == 12
    assert [row.documents for row in rows[:4]] == [0, 1, 3, 4]
    assert rows[0].result.caught == 0
    assert rows[1].result.caught > 0
    assert rows[1].result.cost_usd == Decimal("0.002")
    assert "synthetic-cultural" in table(rows)

    factory = clubops_predictor(ModelClient(load_settings()), tmp_path)
    first = factory(packs[0], packs[0].documents[:1])
    second = factory(packs[1], packs[1].documents[:1])
    first_store = first.store_for(cases[0])
    second_store = second.store_for(cases[0])
    try:
        assert first_store.backend.versions("kh-synthetic-academic-a1")
        assert not second_store.backend.versions("kh-synthetic-academic-a1")
    finally:
        first_store.close()
        second_store.close()


def test_changed_starter_file_is_rejected_before_a_run(tmp_path: Path) -> None:
    path = tmp_path / "changed.json"
    path.write_text(Path("eval/new-club-starters.json").read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since their freeze"):
        load_packs(path, Path("eval/synthetic-events.csv"))


def test_checklist_cli_proves_pipeline_without_claiming_model_curve() -> None:
    run = subprocess.run(
        [sys.executable, "scripts/eval_new_club.py", "--system", "checklist"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "# Synthetic new-club checklist curve" in run.stdout
    assert run.stdout.count("| synthetic-") == 12
    assert "| synthetic-academic | academic | 0 |" in run.stdout


def test_missing_model_replays_never_write_a_curve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "reported.md"
    monkeypatch.setattr(sys, "argv", ["eval_new_club.py", "--out", str(output)])
    monkeypatch.setattr(new_club, "load_packs", lambda _starters, _events: ([], []))
    monkeypatch.setattr(
        new_club,
        "run_curve",
        lambda _packs, _cases, _predictor: [new_club.CurveRow("x", "academic", 0, 1, Score(errors=1))],
    )
    with pytest.raises(ValueError, match="replay is incomplete"):
        new_club.main()
    assert not output.exists()
