"""C-27: learn -> sandbox approval -> cited follow-up, replay by default; never uses a production store.

python scripts/eval_learning.py --cases <private.csv> --as-of YYYY-MM-DD --out results/tmp/learning.md
Only --mode record/live can call a provider. Each case gets its own empty memory and a shared $0.05/8-step budget.
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
from clubops.config import ModelMode, load_settings
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
from clubops.evaluation.learning import Case, Columns, Phase, Trial, evaluate, markdown, parse_cases
from clubops.knowhow.store import KnowHowStore
from clubops.learning.capture import Learner
from clubops.model import ModelRequest
from clubops.model.budget import Budget
from clubops.model.client import ModelClient

MAX_COST = Decimal("0.05")
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--as-of", type=_date, required=True, help="fixed evaluation date, also used for stable replay")
    parser.add_argument("--mode", choices=[mode.value for mode in ModelMode], default="replay")
    parser.add_argument("--dataset-kind", choices=["private", "synthetic"], default="private")
    parser.add_argument("--source-column", default="source")
    parser.add_argument("--question-column", default="question")
    parser.add_argument("--expected-column", default="expected_facts")
    parser.add_argument("--expected-format", choices=["json", "text"], default="json")
    parser.add_argument("--kind-column", default="source_kind")
    parser.add_argument("--club-column", default="club_id")
    parser.add_argument(
        "--recordings", type=Path, help="private recording directory; keep identical between record/replay"
    )
    parser.add_argument("--out", type=Path, help="metadata-only Markdown report")
    parser.add_argument("--json-out", type=Path, help="metadata-only machine-readable report")
    args = parser.parse_args(argv)
    outputs = [path.resolve() for path in (args.out, args.json_out) if path is not None]
    if len(set(outputs)) != len(outputs) or args.cases.resolve() in outputs:
        parser.error("Report paths must be distinct and cannot overwrite the dataset.")
    try:
        columns = Columns(
            args.source_column,
            args.question_column,
            args.expected_column,
            args.kind_column,
            args.club_column,
            args.expected_format,
        )
        snapshot = args.cases.read_bytes()
        cases = parse_cases(snapshot.decode("utf-8-sig"), columns)
        env = {**os.environ, "CLUBOPS_MODEL_MODE": args.mode}
        if args.recordings is not None:
            env["CLUBOPS_RECORDINGS_DIR"] = str(args.recordings)
        settings = load_settings(env=env)
    except (OSError, ValueError, UnicodeError):
        parser.error(
            "Cannot load learning cases/configuration. Check the documented CSV schema; private values omitted."
        )
    report = evaluate(cases, make_system(TrackedClient(settings), args.as_of), args.as_of)
    report.update(
        {
            "dataset_sha256": hashlib.sha256(snapshot).hexdigest(),
            "dataset_kind": args.dataset_kind,
            "mode": args.mode,
            "sandbox_approval": True,
            "cost_accounting": (
                "Shared per-case budget records successful and failed spend, not a reconciled provider bill. "
                "Replay charges zero budget cost; it does not estimate historical operating cost."
            ),
        }
    )
    text = markdown(report) + f"\nMode: {args.mode}; dataset: {args.dataset_kind}; sandbox approval only.\n"
    for path, content in [(args.out, text), (args.json_out, json.dumps(report, indent=2) + "\n")]:
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(text)
    return 2 if report["totals"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
