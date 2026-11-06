"""Experiment tracking for evaluation runs (MLflow).

Every evaluation run is logged with what produced it (model, prompt versions, settings, the hash of the
test file) and what came out (scores, cost, errors, time). The store lives in a private folder
(``CLUBOPS_TRACKING_DIR``, default ``data/private/mlflow``): runs are logged against private test data,
so nothing here is committed. Only scores, ids and codes are logged, never event text.

MLflow is an optional dependency (``uv sync --extra tracking``). Without it, or without ``--track``,
tracking does nothing, so CI and the app never need it. Browse the runs with:

    uv run --extra tracking mlflow ui --backend-store-uri sqlite:///data/private/mlflow/mlflow.db
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

DEFAULT_DIR = Path("data/private/mlflow")


def file_hash(path: Path) -> str:
    """Short SHA-256 of a test file, so a run says exactly which (frozen) version it used."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


class Tracker(Protocol):
    def log_run(
        self,
        name: str,
        params: Mapping[str, Any],
        metrics: Mapping[str, float],
        tags: Mapping[str, str],
        tables: Mapping[str, str],
    ) -> None: ...


class NullTracker:
    """Tracking switched off."""

    def log_run(
        self,
        name: str,
        params: Mapping[str, Any],
        metrics: Mapping[str, float],
        tags: Mapping[str, str],
        tables: Mapping[str, str],
    ) -> None:
        return None


class MlflowTracker:
    """Logs each run to a local MLflow store (SQLite + artifact folder) under ``root``."""

    def __init__(self, experiment: str, root: Path = DEFAULT_DIR) -> None:
        os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
        import mlflow  # optional dependency, imported only when tracking is asked for

        root.mkdir(parents=True, exist_ok=True)
        self._mlflow = mlflow
        mlflow.set_tracking_uri(f"sqlite:///{(root / 'mlflow.db').resolve()}")
        if mlflow.get_experiment_by_name(experiment) is None:
            mlflow.create_experiment(experiment, artifact_location=(root / "artifacts").resolve().as_uri())
        mlflow.set_experiment(experiment)

    def log_run(
        self,
        name: str,
        params: Mapping[str, Any],
        metrics: Mapping[str, float],
        tags: Mapping[str, str],
        tables: Mapping[str, str],
    ) -> None:
        mlflow = self._mlflow
        with mlflow.start_run(run_name=name, tags=dict(tags)):
            mlflow.log_params({k: str(v) for k, v in params.items()})
            mlflow.log_metrics(dict(metrics))
            for file_name, text in tables.items():
                mlflow.log_text(text, file_name)


def tracker(experiment: str | None, root: Path | None = None) -> Tracker:
    """``experiment`` None means no tracking. ``root`` defaults to ``CLUBOPS_TRACKING_DIR`` or DEFAULT_DIR."""
    if not experiment:
        return NullTracker()
    where = root or Path(os.environ.get("CLUBOPS_TRACKING_DIR") or DEFAULT_DIR)
    return MlflowTracker(experiment, where)
