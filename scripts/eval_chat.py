"""Test the chatbot on the private question file. You mark the answers; code counts them (J-17).

Step 1, ask:   python scripts/eval_chat.py ask --cases <questions.csv> --out <sheet.csv> --as-of 2026-11-24
Step 2, mark:  open the sheet, fill `correct` (yes / partly / no) and `sources_ok` (yes / no) where empty.
Step 3, score: python scripts/eval_chat.py score --sheet <sheet.csv>

The question file is read as it is (q_id, question, expected, answer). The sheet holds private text: it is
refused inside this repository. The chatbot answers from the club's real approved facts (the app's data folder).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clubops.chat.ask import ask
from clubops.config import _read_dotenv, load_settings
from clubops.contracts.knowhow import Answer, AskRequest
from clubops.evaluation.chat_sheet import ask_sheet, read_questions, read_sheet, score_sheet, table, write_sheet
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore
from clubops.model.client import ModelClient
from clubops.redaction import redact

REPO = Path(__file__).resolve().parents[1]


def _outside_repo(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == REPO or REPO in resolved.parents:
        raise SystemExit("The sheet holds private answers: choose a path outside the ClubOps folder.")
    return resolved


def run_ask(args: argparse.Namespace) -> None:
    out = _outside_repo(args.out)
    settings = load_settings()
    questions = read_questions(args.cases)
    if args.limit:
        questions = questions[: args.limit]
    values = {**_read_dotenv(Path(".env")), **os.environ}  # the same folder the running app uses
    data_dir = Path(args.data_dir or values.get("CLUBOPS_DATA_DIR") or "data/app")
    print(f"Model mode: {settings.mode.value}. Questions: {len(questions)}.")
    store = KnowHowStore(open_club_store_backend(data_dir, args.club))
    facts = store.current(args.club, args.as_of)
    print(f"Data folder: {data_dir.resolve()}\nApproved facts the chatbot can use for {args.club}: {len(facts)}.")
    client = ModelClient(settings)

    def answer(text: str) -> tuple[Answer, Decimal, list[str]]:
        spent = settings.new_budget()
        request = AskRequest(club_id=args.club, question=text, as_of=args.as_of)
        reply = ask(request, store, client, spent)
        titles = [item.title for cited in reply.citations if (item := store.latest(cited)) is not None]
        return reply, Decimal(str(spent.spent_usd)), titles

    try:
        rows = ask_sheet(questions, answer)
    finally:
        store.close()
    write_sheet(out, rows)
    total = sum((Decimal(r["cost_usd"]) for r in rows), Decimal("0"))
    print(f"Sheet written: {out}\nCost: ${total:.4f}")
    to_mark = sum(1 for r in rows if r["expected"] == "known" and r["clubops_known"] == "yes")
    print(f"Now mark {to_mark} rows: fill `correct` (yes/partly/no) and `sources_ok` (yes/no).")


def run_search(args: argparse.Namespace) -> None:
    """Free: what the chatbot's search finds for each question, before any model call."""
    values = {**_read_dotenv(Path(".env")), **os.environ}
    data_dir = Path(args.data_dir or values.get("CLUBOPS_DATA_DIR") or "data/app")
    store = KnowHowStore(open_club_store_backend(data_dir, args.club))
    try:
        print(f"Data folder: {data_dir.resolve()}")
        print(f"Approved facts for {args.club}: {len(store.current(args.club, args.as_of))}.")
        empty = []
        for q in read_questions(args.cases):
            found = [i for i in store.search(args.club, redact(q.question).text) if i.is_current(args.as_of)]
            club_facts = sum(i.club_id is not None for i in found)
            line = f"{q.q_id} ({q.expected}): {len(found)} facts found, {club_facts} from the club"
            if args.titles:
                line += " | " + "; ".join(i.title for i in found[:3])
            print(line)
            if not found:
                empty.append(q.q_id)
        print(f"Questions with no facts found: {len(empty)}" + (f" ({', '.join(empty)})" if empty else ""))
    finally:
        store.close()


def run_score(args: argparse.Namespace) -> None:
    rows = read_sheet(args.sheet)
    if args.counts:  # free, before any marking: how many answered, said not sure, or failed
        for expected in ("known", "not_sure"):
            part = [r for r in rows if r["expected"] == expected]
            print(
                f"expected {expected}: {len(part)} questions; "
                f"answered {sum(r['clubops_known'] == 'yes' for r in part)}, "
                f"said not sure {sum(r['clubops_known'] == 'no' for r in part)}, "
                f"errors {sum(r['clubops_known'] == 'error' for r in part)}"
            )
        return
    try:
        result = score_sheet(rows, frozenset(i.strip().upper() for i in args.exclude.split(",") if i.strip()))
    except ValueError as problem:
        raise SystemExit(str(problem)) from problem
    left_out = ", ".join(sorted(i.strip().upper() for i in args.exclude.split(",") if i.strip()))
    note = f"; left out of the count: {left_out}" if left_out else ""
    rendered = f"# Chatbot evaluation ({result['questions']} questions{note})\n\n{table(result)}\n"
    if args.out is not None:
        _outside_repo(args.out).write_text(rendered, encoding="utf-8")
    print(rendered)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    steps = parser.add_subparsers(dest="step", required=True)
    first = steps.add_parser("ask", help="ask every question and write the marking sheet")
    first.add_argument("--cases", required=True, type=Path)
    first.add_argument("--out", required=True, type=Path)
    first.add_argument("--as-of", type=date.fromisoformat, required=True)
    first.add_argument("--club", default="running-club")
    first.add_argument(
        "--data-dir", help="the app's data folder (default: CLUBOPS_DATA_DIR from the environment or .env)"
    )
    first.add_argument("--limit", type=int, default=0, help="only the first N questions (a cheap trial)")
    first.set_defaults(run=run_ask)
    look = steps.add_parser("search", help="free: how many facts the search finds for each question")
    look.add_argument("--cases", required=True, type=Path)
    look.add_argument("--as-of", type=date.fromisoformat, required=True)
    look.add_argument("--club", default="running-club")
    look.add_argument("--data-dir")
    look.add_argument("--titles", action="store_true", help="also print the first 3 fact titles (private)")
    look.set_defaults(run=run_search)
    second = steps.add_parser("score", help="count a marked sheet")
    second.add_argument("--sheet", required=True, type=Path)
    second.add_argument("--out", type=Path)
    second.add_argument("--exclude", default="", help="question ids to leave out of the count, e.g. Q18")
    second.add_argument(
        "--counts", action="store_true", help="only count answered / not sure / errors (no marking needed)"
    )
    second.set_defaults(run=run_score)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
