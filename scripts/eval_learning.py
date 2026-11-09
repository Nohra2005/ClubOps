"""C-27: export a private evidence sheet, then summarize the human-completed ratings.

export --cases <private.csv> --as-of YYYY-MM-DD --sheet data/private/learning-review.csv
score --sheet data/private/learning-review.csv --out results/tmp/learning.md
Only export/smoke with explicit --mode record/live can call a provider; score is offline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clubops.capabilities.runner import Usage
from clubops.chat.ask import ask
from clubops.config import ModelMode, Settings, load_settings
from clubops.contracts.common import Actor, Role, SourceRef, Untrusted
from clubops.contracts.knowhow import (
    Answer,
    AskRequest,
    CaptureRequest,
    KnowHowItem,
    ProposalOp,
    Scope,
    VerifyDecision,
    VerifyRequest,
)
from clubops.evaluation.learning import (
    Case,
    Columns,
    Phase,
    Trial,
    collect_trials,
    evaluate,
    human_markdown,
    markdown,
    parse_cases,
    summarize_ratings,
    write_review,
)
from clubops.knowhow.store import KnowHowStore
from clubops.learning.capture import Learner
from clubops.model import ModelRequest
from clubops.model.budget import Budget
from clubops.model.client import ModelClient

MAX_COST = Decimal("0.05")
ROOT = Path(__file__).resolve().parents[1]
T = TypeVar("T", bound=BaseModel)


class TrackedClient(ModelClient):
    """Retain an error count even if a capability converts a failed model call into a fallback."""

    failed_calls = 0

    def complete(self, request: ModelRequest, output: type[T], budget: Budget | None = None) -> tuple[T, Usage]:
        try:
            return super().complete(request, output, budget)
        except Exception:
            self.failed_calls += 1
            raise


def make_system(client: TrackedClient, on: date) -> Callable[[Case], Trial]:
    """Task-authorized composition of public interfaces; labels are never passed to either model call."""
    now = datetime.combine(on, time(12), UTC)

    def run(case: Case) -> Trial:
        store = KnowHowStore()
        budget = Budget(max_usd=MAX_COST, max_steps=8)
        before: Answer | None = None
        after: Answer | None = None
        proposed: tuple[KnowHowItem, ...] = ()
        approved: tuple[KnowHowItem, ...] = ()
        phase: Phase = "baseline"
        error: Phase | None = None
        failed_at_start = client.failed_calls
        try:
            question = AskRequest(club_id=case.club_id, question=case.question, as_of=on)
            before = ask(question, store, client, budget)
            if client.failed_calls != failed_at_start:
                raise ValueError("Baseline used a failed model call.")
            phase = "capture"
            request = CaptureRequest(
                club_id=case.club_id,
                sources=[
                    Untrusted(
                        content=case.source,
                        source=SourceRef(kind=case.kind, source_id=f"learning-eval/{case.ref}", observed_at=now),
                    )
                ],
            )
            captured = Learner(client, store).capture(request, on, budget)
            if client.failed_calls != failed_at_start:
                raise ValueError("Capture used a failed model call.")
            # Stable case-local IDs keep the follow-up request identical for record -> replay.
            proposals = [
                proposal.model_copy(
                    update={
                        "proposal_id": f"eval-{case.ref}-{index}",
                        "candidate": proposal.candidate.model_copy(update={"item_id": f"kh-learn-{case.ref}-{index}"}),
                    }
                )
                for index, proposal in enumerate(captured.proposals, 1)
            ]
            proposed = tuple(proposal.candidate for proposal in proposals)
            phase = "approval"
            reviewer = Actor(
                member_id="m-eval-reviewer", club_id=case.club_id, roles=frozenset({Role.PRESIDENT}), verified=True
            )
            for proposal in proposals:
                candidate = proposal.candidate
                if (
                    proposal.op is not ProposalOp.CREATE
                    or candidate.scope is not Scope.CLUB
                    or candidate.club_id != case.club_id
                ):
                    raise ValueError("Unexpected proposal in an isolated learning case.")
                store.submit(proposal)
                outcome = store.verify(VerifyRequest(proposal=proposal, decision=VerifyDecision.ACCEPT), reviewer, now)
                if outcome.data is None or outcome.data.committed is None:
                    raise ValueError("Sandbox approval did not commit a fact.")
            phase = "answer"
            after = ask(question, store, client, budget)
            if client.failed_calls != failed_at_start:
                raise ValueError("Answer used a failed model call.")
        except Exception:
            error = phase  # no raw provider, source, label or answer contents in the report
        finally:
            approved = tuple(store.current(case.club_id, on))
            store.close()
        return Trial(proposed, approved, before, after, budget.spent_usd, budget.steps, error)

    return run


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD.") from None


def _run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--as-of", type=_date, required=True, help="fixed evaluation date, also used for stable replay")
    parser.add_argument("--mode", choices=[mode.value for mode in ModelMode], default="replay")
    parser.add_argument("--model", help="public model identifier; otherwise use the configured model")
    parser.add_argument("--dataset-kind", choices=["private", "synthetic"], default="private")
    parser.add_argument("--source-column", default="source")
    parser.add_argument("--question-column", default="question")
    parser.add_argument("--expected-column", default="expected_facts")
    parser.add_argument("--expected-format", choices=["json", "text"], default="json")
    parser.add_argument("--kind-column", default="source_kind")
    parser.add_argument("--club-column", default="club_id")
    parser.add_argument("--id-column", default="id", help="optional original case ID column, exported only privately")
    parser.add_argument(
        "--recordings", type=Path, help="private recording directory; keep identical between record/replay"
    )


def _report_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out", type=Path, help="metadata-only Markdown results (.md)")
    parser.add_argument("--json-out", type=Path, help="metadata-only machine-readable results (.json)")


def _distinct(parser: argparse.ArgumentParser, inputs: Sequence[Path], outputs: Sequence[Path]) -> None:
    destinations = [path.resolve() for path in outputs]
    if len(set(destinations)) != len(destinations) or set(destinations) & {path.resolve() for path in inputs}:
        parser.error("Output paths must be distinct and cannot overwrite inputs.")


def _load(args: argparse.Namespace, parser: argparse.ArgumentParser) -> tuple[list[Case], bytes, Settings]:
    try:
        columns = Columns(
            source=args.source_column,
            question=args.question_column,
            expected=args.expected_column,
            kind=args.kind_column,
            club=args.club_column,
            expected_format=args.expected_format,
            id=args.id_column,
        )
        snapshot = args.cases.read_bytes()
        cases = parse_cases(snapshot.decode("utf-8-sig"), columns)
        env = {**os.environ, "CLUBOPS_MODEL_MODE": args.mode}
        if args.model is not None:
            env["CLUBOPS_MODEL"] = args.model
        if args.recordings is not None:
            env["CLUBOPS_RECORDINGS_DIR"] = str(args.recordings)
        settings = load_settings(env=env)
    except (OSError, ValueError, UnicodeError):
        parser.error(
            "Cannot load learning cases/configuration. Check the documented CSV schema; private values omitted."
        )
    return cases, snapshot, settings


def _metadata(args: argparse.Namespace, snapshot: bytes, settings: Settings) -> dict[str, object]:
    return {
        "dataset_sha256": hashlib.sha256(snapshot).hexdigest(),
        "dataset_kind": args.dataset_kind,
        "mode": args.mode,
        "model": settings.model,
        "price_in_per_mtok": str(settings.price_in_per_mtok),
        "price_out_per_mtok": str(settings.price_out_per_mtok),
        "budget_usd_per_case": str(MAX_COST),
        "max_steps_per_case": 8,
        "sandbox_approval": True,
        "cost_accounting": (
            "Shared per-case budget records successful and failed spend, not a reconciled provider bill. "
            "Replay charges zero budget cost; it does not estimate historical operating cost."
        ),
    }


def _write_reports(args: argparse.Namespace, text: str, report: dict[str, object]) -> None:
    for path, content in [(args.out, text), (args.json_out, json.dumps(report, indent=2) + "\n")]:
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="run once and write the seven-column private review CSV")
    _run_arguments(export)
    export.add_argument("--sheet", type=Path, required=True)
    export.add_argument("--manifest", type=Path, help="companion run metadata; defaults to <sheet>.run.json")
    score = commands.add_parser("score", help="offline results from the completed yes/partly/no ratings")
    score.add_argument("--sheet", type=Path, required=True)
    score.add_argument("--manifest", type=Path)
    _report_arguments(score)
    smoke = commands.add_parser("smoke", help="technical exact-word diagnostic only, not semantic quality")
    _run_arguments(smoke)
    _report_arguments(smoke)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command in ("export", "score"):
        args.manifest = args.manifest or args.sheet.with_suffix(".run.json")
        if args.sheet.suffix.lower() != ".csv" or args.manifest.suffix.lower() != ".json":
            parser.error("Use a .csv review sheet and .json companion.")
    if args.command != "export":
        outputs = [path for path in (args.out, args.json_out) if path is not None]
        inputs = [args.sheet, args.manifest] if args.command == "score" else [args.cases]
        _distinct(parser, inputs, outputs)
        if (args.out and args.out.suffix.lower() != ".md") or (
            args.json_out and args.json_out.suffix.lower() != ".json"
        ):
            parser.error("Result files must use .md and .json extensions.")
    if args.command == "score":
        try:
            report = summarize_ratings(args.sheet.read_bytes(), args.manifest.read_bytes())
            text = human_markdown(report)
            _write_reports(args, text, report)
        except (OSError, ValueError) as error:
            parser.error(
                str(error)
                if isinstance(error, ValueError)
                else "Cannot read/write review files; private values omitted."
            )
        print(text)
        return 2 if report["totals"]["errors"] else 0
    if args.command == "export":
        _distinct(parser, [args.cases], [args.sheet, args.manifest])
        if args.sheet.exists() or args.manifest.exists():
            parser.error("Choose new review output paths; existing ratings are never overwritten.")
        if args.dataset_kind == "private":
            for path in (args.sheet, args.manifest):
                resolved = path.resolve()
                if resolved.is_relative_to(ROOT) and not any(
                    resolved.is_relative_to(ROOT / folder) for folder in ("data/private", "results/tmp")
                ):
                    parser.error(
                        "Private review text must stay in data/private, results/tmp, or outside the repository."
                    )
    cases, snapshot, settings = _load(args, parser)
    metadata = _metadata(args, snapshot, settings)
    system = make_system(TrackedClient(settings), args.as_of)
    if args.command == "export":
        try:
            run = write_review(
                cases,
                collect_trials(cases, system),
                args.as_of,
                sheet=args.sheet,
                manifest=args.manifest,
                metadata=metadata,
            )
        except (OSError, ValueError):
            parser.error(
                "Cannot create a new review sheet/companion; no text was truncated and private values omitted."
            )
        errors = sum(row["error"] is not None for row in run["cases"])
        print(json.dumps({"cases": len(cases), "errors": errors, "ratings": "blank", "mode": args.mode}))
        return 2 if errors else 0
    report = evaluate(cases, system, args.as_of)
    report.update(metadata)
    report["diagnostic_only"] = True
    text = markdown(report) + (
        f"\nMode: {args.mode}; dataset: {args.dataset_kind}; sandbox approval only.\n"
        f"Configured USD per million tokens: input {settings.price_in_per_mtok}, output {settings.price_out_per_mtok}. "
        "These are accounting assumptions, not verification of the provider's price.\n"
    )
    _write_reports(args, text, report)
    print(text)
    return 2 if report["totals"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
