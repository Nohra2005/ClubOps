"""Club-bound report assembly. Planning snapshots and traces are overlapping views, not additive costs."""

from pathlib import Path
from typing import Any

from clubops.reports.runs import read_runs, run_path, summarize_runs
from clubops.reports.traces import summarize_traces, trace_path


def usage_details(data_dir: Path, club_id: str, month: str) -> dict[str, Any]:
    runs = read_runs(run_path(data_dir, club_id))
    traces = summarize_traces(trace_path(data_dir, club_id), month)
    return {
        "run_metrics": summarize_runs(runs, month),
        "trace_metrics": traces,
        "trace_metrics_available": bool(traces),
        "metrics_note": (
            "Run outcomes cover recorded planning activity. Detailed model metrics appear when traces are recorded."
        ),
    }


def build_report(data_dir: Path, club_id: str, month: str) -> dict[str, Any]:
    return {
        "report_version": 1,
        "club_id": club_id,
        "month": month,
        **usage_details(data_dir, club_id, month),
        "cost_accounting": "Run spend and trace spend overlap. They are separate views and must not be added together.",
        "scope": (
            "Only this club's recorded metadata is read. Missing trace metrics are unavailable, not measured zero."
        ),
    }
