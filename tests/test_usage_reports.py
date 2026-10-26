"""C-20 report and CLI: scoped data, explicit missing metrics and no double-counted combined total."""

import json
import sys
from pathlib import Path

import pytest

from clubops.contracts.common import Status
from clubops.reports.__main__ import main
from clubops.reports.traces import record_trace
from clubops.reports.usage import build_report
from tests.test_trace_reports import trace


def test_reports_and_cli_do_not_read_global_or_foreign_trace_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_trace(tmp_path, "running-club", trace(), Status.OK, None)
    own = build_report(tmp_path, "running-club", "2026-10")
    other = build_report(tmp_path, "asme", "2026-10")
    assert own["trace_metrics_available"] and own["trace_metrics"][0]["tokens_in"] == 100
    assert not other["trace_metrics_available"] and other["trace_metrics"] == []
    assert own["run_metrics"]["cost_per_successful_plan"] is None
    assert "must not be added" in own["cost_accounting"]
    target = tmp_path / "results" / "usage.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reports",
            "--data-dir",
            str(tmp_path),
            "--club",
            "running-club",
            "--month",
            "2026-10",
            "--output",
            str(target),
        ],
    )
    main()
    assert json.loads(target.read_text())["trace_metrics"] == own["trace_metrics"]
