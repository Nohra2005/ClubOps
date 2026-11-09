"""Run the planning evaluation: checklist vs plain model vs model + rulebook vs ClubOps (T-06, T-26).

  uv run python scripts/eval_plans.py --events data/private/d5/d5-events.csv \\
      --facts data/private/d5/facts-learned.csv --runs 3 --out results/plans.md

Model calls follow CLUBOPS_MODEL_MODE: `replay` (default, free, from recordings), `record` (real calls,
saved for replay) or `live`. The test files are private (eval/FROZEN.md); only the result table is written.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Callable
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `python scripts/eval_plans.py` finds `scripts`

from scripts.load_rulebook import read_rulebook

from clubops.agent.planner import PROMPT_VERSION as PLANNER_VERSION
from clubops.agent.planner import ModelDecider, Planner
from clubops.agent.rules_judge import PROMPT_VERSION as JUDGE_VERSION
from clubops.agent.rules_judge import RuleJudge
from clubops.config import load_settings
from clubops.evaluation.plans import (
    PLAIN_VERSION,
    RULEBOOK_VERSION,
    Case,
    ClubOpsSystem,
    Score,
    checklist,
    codes_by_rule,
    facts_before,
    load_cases,
    model_baseline,
    rulebook_text,
    score,
    table,
)
from clubops.evaluation.tracking import Tracker, file_hash, tracker
from clubops.knowhow.directory import Directory
from clubops.knowhow.store import KnowHowStore
from clubops.model.client import ModelClient

SYSTEMS = ("checklist", "plain", "rulebook", "clubops")


def clubops_system(
    client: ModelClient, facts: Path | None, cases: list[Case], work: Path, run: int = 1
) -> ClubOpsSystem:
    rules = read_rulebook()

    def store_for(case: Case) -> KnowHowStore:
        store = KnowHowStore()
        for r in rules:
            store.backend.append(r)
        if facts is not None:
            for f in facts_before(facts, cases, case.on, "eval-club"):
                store.backend.append(f)
        return store

    def directory_for(case: Case) -> Directory:
        return Directory(work / f"{case.case_id}-r{run}", "eval-club")

    def make(store: KnowHowStore, directory: Directory, _: object) -> Planner:
        settings = load_settings()
        variant = f"r{run}" if run > 1 else ""
        return Planner(
            ModelDecider(client, variant=variant),
            store,
            directory,
            step_limit=settings.max_steps_per_plan,
            cost_limit_usd=settings.budget_usd_per_packet,
            rules=RuleJudge(client, variant=variant),
        )

    return ClubOpsSystem(make, store_for, directory_for, codes_by_rule(rules))


VERSIONS = {"plain": PLAIN_VERSION, "rulebook": RULEBOOK_VERSION, "clubops": f"{PLANNER_VERSION}+{JUDGE_VERSION}"}


def log_run(  # noqa: PLR0917  (a one-place script helper; keyword-only would only add noise)
    track: Tracker,
    label: str,
    system: str,
    run: int,
    args: argparse.Namespace,
    cases: list[Case],
    result: Score,
    tags: dict[str, str],
) -> None:
    """One MLflow run per system and repeat: settings in, scores out. Ids and codes only, no event text."""
    settings = load_settings()
    params = {
        "system": system,
        "run": run,
        "model": settings.model if system != "checklist" else "none",
        "prompt_version": VERSIONS.get(system, "none"),
        "mode": settings.mode.value,
        "reasoning_effort": settings.reasoning_effort or "none",
        "step_limit": settings.max_steps_per_plan,
        "cost_limit_usd": settings.budget_usd_per_packet,
        "events_file": args.events.name,
        "events_sha": file_hash(args.events),
        "facts_sha": file_hash(args.facts) if args.facts else "none",
        "events": ",".join(c.case_id for c in cases),
        "start": "short" if args.short_start else "full",
    }
    metrics = {
        "recall": result.recall,
        "precision": result.precision,
        "f1": result.f1,
        "caught": result.caught,
        "missed": result.missed,
        "false_alarms": result.false_alarms,
        "unsure_caught": result.unsure_caught,
        "found_or_flagged": result.found_or_flagged,
        "errors": result.errors,
        "model_calls": result.calls,
        "cost_usd": float(result.cost_usd),
        "cost_per_event_usd": float(result.cost_usd) / max(len(cases), 1),
        "seconds_per_event": result.seconds / max(len(cases), 1),
        "model_seconds_per_event": result.model_seconds / max(len(cases), 1),
        "tool_seconds_per_event": result.tool_seconds / max(len(cases), 1),
    }
    tables = {"result.md": table({label: result}, len(cases)), "rows.json": json.dumps(result.rows, indent=1)}
    track.log_run(label, params, metrics, tags, tables)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--facts", type=Path, default=None)
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=list(SYSTEMS))
    parser.add_argument("--runs", type=int, default=1, help="repeat model systems (each run is recorded separately)")
    parser.add_argument("--only", nargs="*", default=None, help="case ids to run (default: all)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--short-start",
        action="store_true",
        help="systems get only the event and date; the agent asks, the simulated user answers from the row",
    )
    parser.add_argument("--track", metavar="EXPERIMENT", default=None, help="log each system's run to MLflow")
    parser.add_argument("--tag", action="append", default=[], metavar="KEY=VALUE", help="extra run tags")
    args = parser.parse_args()
    track = tracker(args.track)
    tags = dict(t.split("=", 1) for t in args.tag)

    cases = [
        c for c in load_cases(args.events, short_start=args.short_start) if not args.only or c.case_id in args.only
    ]
    client = ModelClient(load_settings())
    results: dict[str, Score] = {}
    with tempfile.TemporaryDirectory() as tmp:
        builders: dict[str, Callable[[int], Callable[[Case], object]]] = {
            "checklist": lambda run: checklist,
            "plain": lambda run: model_baseline(client, None, run),
            "rulebook": lambda run: model_baseline(client, rulebook_text(read_rulebook()), run),
            "clubops": lambda run: clubops_system(client, args.facts, cases, Path(tmp), run),
        }
        for name in args.systems:
            runs = 1 if name == "checklist" else args.runs
            for run in range(1, runs + 1):
                label = name if runs == 1 else f"{name} (run {run})"
                results[label] = score(cases, builders[name](run))  # type: ignore[arg-type]
                log_run(track, label, name, run, args, cases, results[label], tags)
    text = f"# Planning evaluation ({date.today()}, {len(cases)} events)\n\n" + table(results, len(cases)) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
