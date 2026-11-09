"""Experiment tracking (MLflow): off by default, and it logs scores and settings only."""

from __future__ import annotations

from pathlib import Path

import pytest

from clubops.evaluation.tracking import NullTracker, file_hash, tracker


def test_no_experiment_means_no_tracking() -> None:
    assert isinstance(tracker(None), NullTracker)
    tracker(None).log_run("x", {}, {}, {}, {})  # does nothing, needs no MLflow


def test_the_file_hash_changes_when_the_test_file_changes(tmp_path: Path) -> None:
    f = tmp_path / "events.csv"
    f.write_text("id\nS01\n")
    first = file_hash(f)
    f.write_text("id\nS02\n")
    assert first != file_hash(f) and len(first) == 16


def test_a_run_is_logged_with_its_settings_scores_and_tables(tmp_path: Path) -> None:
    mlflow = pytest.importorskip("mlflow")  # optional dependency: `uv sync --extra tracking`
    t = tracker("eval-test", tmp_path / "mlflow")
    t.log_run(
        "clubops",
        {"model": "fake-model", "events_sha": "abc"},
        {"recall": 0.75},
        {"trial": "t1"},
        {"result.md": "| x |"},
    )
    runs = mlflow.search_runs(experiment_names=["eval-test"])
    assert runs.loc[0, "params.model"] == "fake-model"
    assert runs.loc[0, "metrics.recall"] == 0.75
    assert runs.loc[0, "tags.trial"] == "t1"
    assert (tmp_path / "mlflow" / "mlflow.db").exists()
