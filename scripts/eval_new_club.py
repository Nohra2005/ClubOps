"""Measure planning at 0, 1, 3 and all synthetic onboarding documents (J-20).

The ClubOps run uses recorded model answers in replay mode only. With no matching
recordings it fails instead of publishing a misleading learning curve. `--system
checklist` is a free deterministic pipeline check, not a ClubOps result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.load_rulebook import read_rulebook

from clubops.agent.planner import ModelDecider, Planner
from clubops.agent.rules_judge import RuleJudge
from clubops.config import ModelMode, load_settings
from clubops.contracts.knowhow import KnowHowItem
from clubops.evaluation.plans import Case, ClubOpsSystem, Prediction, Score, checklist, codes_by_rule, load_cases, score
from clubops.knowhow.directory import Directory
from clubops.knowhow.store import KnowHowStore
from clubops.model.budget import Budget
from clubops.model.client import ModelClient

STARTERS_SHA = "4dcc774a8485e03907fbc403df2533635c0cb2e3ae065a4909420aef4b3a3e3d"
EVENTS_SHA = "bcec66154ec2dbafcd65af0e2a9e46828c5cdab11e4cd681c4372f4432a84006"
STAGES = (0, 1, 3, 4)


@dataclass(frozen=True)
class StarterDocument:
    doc_id: str
    on: date
    statement: str


@dataclass(frozen=True)
class ClubPack:
    club_id: str
    kind: str
    event_ids: tuple[str, ...]
    documents: tuple[StarterDocument, ...]


@dataclass(frozen=True)
class CurveRow:
    club_id: str
    kind: str
    documents: int
    events: int
    result: Score


def _frozen_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(bytes([13, 10]), bytes([10]))).hexdigest()


def load_packs(path: Path, events: Path) -> tuple[list[ClubPack], list[Case]]:
    if _frozen_hash(path) != STARTERS_SHA or _frozen_hash(events) != EVENTS_SHA:
        raise ValueError("synthetic new-club inputs changed since their freeze; review and re-freeze before running")
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = load_cases(events)
    by_id = {case.case_id: case for case in cases}
    packs: list[ClubPack] = []
    used: set[str] = set()
    for entry in raw["clubs"]:
        ids = tuple(entry["event_ids"])
        if len(ids) < 2 or any(case_id not in by_id or case_id in used for case_id in ids):
            raise ValueError("each synthetic club needs two unique frozen events")
        used.update(ids)
        docs = tuple(
            StarterDocument(doc["id"], date.fromisoformat(doc["on"]), doc["statement"]) for doc in entry["documents"]
        )
        if len(docs) != 4 or any(doc.on >= min(by_id[case_id].on for case_id in ids) for doc in docs):
            raise ValueError("four starter documents must predate every evaluated event")
        packs.append(ClubPack(entry["club_id"], entry["kind"], ids, docs))
    if len(packs) != 3 or {pack.kind for pack in packs} != {"academic", "cultural", "social"}:
        raise ValueError("the frozen set needs academic, cultural and social clubs")
    return packs, cases


PredictorFactory = Callable[[ClubPack, tuple[StarterDocument, ...]], Callable[[Case], Prediction]]


def run_curve(packs: list[ClubPack], cases: list[Case], make_predictor: PredictorFactory) -> list[CurveRow]:
    by_id = {case.case_id: case for case in cases}
    rows: list[CurveRow] = []
    for pack in packs:
        selected = [by_id[case_id] for case_id in pack.event_ids]
        for count in STAGES:
            result = score(selected, make_predictor(pack, pack.documents[:count]))
            rows.append(CurveRow(pack.club_id, pack.kind, count, len(selected), result))
    return rows


def _fact(pack: ClubPack, doc: StarterDocument) -> KnowHowItem:
    observed = datetime.combine(doc.on, datetime.min.time(), tzinfo=UTC)
    return KnowHowItem.model_validate(
        {
            "item_id": f"kh-{pack.club_id}-{doc.doc_id}",
            "scope": "club",
            "club_id": "eval-club",  # ClubOpsSystem's isolated synthetic request club
            "title": doc.statement[:80],
            "statement": doc.statement,
            "details": {"kind": "decision", "decision": doc.statement[:300], "rationale": "synthetic starter document"},
            "sources": [{"kind": "document", "source_id": f"{pack.club_id}/{doc.doc_id}", "observed_at": observed}],
            "support": {"events": [], "source_count": 1},
            "status": "verified",
            "verified_by": "m-synthetic-president",
            "verified_at": observed,
            "version": 1,
        }
    )


def clubops_predictor(client: ModelClient, work: Path) -> PredictorFactory:
    rules = read_rulebook()
    settings = load_settings()

    def build(pack: ClubPack, documents: tuple[StarterDocument, ...]) -> Callable[[Case], Prediction]:
        stage = len(documents)

        def store_for(_: Case) -> KnowHowStore:
            store = KnowHowStore()
            for item in rules:
                store.backend.append(item)
            for doc in documents:
                store.backend.append(_fact(pack, doc))
            return store

        def directory_for(case: Case) -> Directory:
            return Directory(work / pack.club_id / f"stage-{stage}" / case.case_id, "eval-club")

        def make(store: KnowHowStore, directory: Directory, _: Budget | None) -> Planner:
            return Planner(
                ModelDecider(client),
                store,
                directory,
                step_limit=settings.max_steps_per_plan,
                cost_limit_usd=settings.budget_usd_per_packet,
                rules=RuleJudge(client),
            )

        return ClubOpsSystem(make, store_for, directory_for, codes_by_rule(rules))

    return build


def table(rows: list[CurveRow]) -> str:
    lines = [
        "| Club | Kind | Documents | Events | Caught | Missed | False alarms | Cost (USD) | Errors |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        result = row.result
        lines.append(
            f"| {row.club_id} | {row.kind} | {row.documents} | {row.events} | {result.caught} | "
            f"{result.missed} | {result.false_alarms} | {result.cost_usd:.4f} | {result.errors} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--starters", type=Path, default=Path("eval/new-club-starters.json"))
    parser.add_argument("--events", type=Path, default=Path("eval/synthetic-events.csv"))
    parser.add_argument("--system", choices=("clubops", "checklist"), default="clubops")
    parser.add_argument("--out", type=Path, help="write only aggregate scores to this file")
    args = parser.parse_args()
    packs, cases = load_packs(args.starters, args.events)
    if args.system == "clubops" and load_settings().mode is not ModelMode.REPLAY:
        raise ValueError("J-20 only runs ClubOps in replay mode; set CLUBOPS_MODEL_MODE=replay")
    with tempfile.TemporaryDirectory() as tmp:
        factory = (
            clubops_predictor(ModelClient(load_settings()), Path(tmp))
            if args.system == "clubops"
            else lambda _pack, _docs: checklist
        )
        rows = run_curve(packs, cases, factory)
    if args.system == "clubops" and any(row.result.errors for row in rows):
        raise ValueError("ClubOps replay is incomplete; add synthetic model recordings before reporting a curve")
    result = f"# Synthetic new-club {args.system} curve\n\n{table(rows)}\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
