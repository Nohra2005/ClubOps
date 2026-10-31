"""Run the planning evaluation: checklist vs plain model vs model + rulebook vs ClubOps (T-06, T-26).

  uv run python scripts/eval_plans.py --events data/private/d5/d5-events.csv \\
      --facts data/private/d5/facts-learned.csv --runs 3 --out results/plans.md

Model calls follow CLUBOPS_MODEL_MODE: `replay` (default, free, from recordings), `record` (real calls,
saved for replay) or `live`. The test files are private (eval/FROZEN.md); only the result table is written.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Callable
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `python scripts/eval_plans.py` finds `scripts`

from scripts.load_rulebook import read_rulebook

from clubops.agent.planner import ModelDecider, Planner
from clubops.agent.rules_judge import RuleJudge
from clubops.config import load_settings
from clubops.evaluation.plans import (
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--facts", type=Path, default=None)
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=list(SYSTEMS))
    parser.add_argument("--runs", type=int, default=1, help="repeat model systems (each run is recorded separately)")
    parser.add_argument("--only", nargs="*", default=None, help="case ids to run (default: all)")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    cases = [c for c in load_cases(args.events) if not args.only or c.case_id in args.only]
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
    text = f"# Planning evaluation ({date.today()}, {len(cases)} events)\n\n" + table(results, len(cases)) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
