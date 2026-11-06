"""The learning phase (T-09): read a club's material the normal way, then review what was learned.

ClubOps reads each file in pieces (the same learning code the app uses), and every fact it finds waits in
Review. The president then decides on a sheet instead of clicking through the app:

  # 1. learn (can be stopped and resumed; finished pieces are skipped)
  uv run python scripts/seed_club.py learn --club running-club --data-dir data/app \\
      --source data/private/club/cabinet.txt:chat_message --source data/private/club/bookings.txt:document

  # 2. write the review sheet, fill the "decision" column (approve / reject / edit + corrected text)
  uv run python scripts/seed_club.py sheet --club running-club --data-dir data/app --out data/private/review.csv

  # 3. apply the decisions, as the president
  uv run python scripts/seed_club.py apply --club running-club --data-dir data/app \\
      --sheet data/private/review.csv --member m-tatiana-nohra

Club material and the sheet are private: keep them under data/private/ (never committed).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `python scripts/seed_club.py` finds `scripts`

from clubops.api.security import MemberStore
from clubops.config import Settings, load_settings
from clubops.contracts.common import SourceKind, SourceRef, Untrusted
from clubops.contracts.knowhow import CaptureRequest, KnowHowProposal, VerifyDecision, VerifyRequest
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore
from clubops.learning.capture import MAX_SOURCE_CHARS, Learner
from clubops.model.client import ModelClient

SHEET_COLUMNS = [
    "proposal_id",
    "type",
    "title",
    "statement",
    "quote",
    "source",
    "known_fact",
    "warning",
    "decision",
    "edited_text",
]


def pieces(text: str, size: int = MAX_SOURCE_CHARS) -> list[str]:
    """Split on line breaks into pieces of at most ``size`` characters (a longer single line is cut)."""
    out: list[str] = []
    current = ""
    for raw in text.splitlines(keepends=True):
        line = raw
        while len(line) > size:
            if current:
                out.append(current)
                current = ""
            out.append(line[:size])
            line = line[size:]
        if len(current) + len(line) > size:
            out.append(current)
            current = ""
        current += line
    if current.strip():
        out.append(current)
    return out


def parse_source(spec: str) -> tuple[Path, SourceKind]:
    path, _, kind = spec.rpartition(":")
    if not path:
        return Path(spec), SourceKind.DOCUMENT
    return Path(path), SourceKind(kind)


def learn(args: argparse.Namespace, client: ModelClient | None = None, settings: Settings | None = None) -> None:
    settings = settings or load_settings()
    state_path = args.data_dir / f"seed-{args.club}.json"
    saved = json.loads(state_path.read_text()) if state_path.exists() else {}
    done: list[str] = list(saved.get("done", []))
    facts = int(saved.get("proposals", 0))
    dropped = int(saved.get("dropped", 0))
    cost = Decimal(str(saved.get("cost", "0")))
    store = KnowHowStore(open_club_store_backend(args.data_dir, args.club))
    learner = Learner(client or ModelClient(settings), store)
    started = time.monotonic()
    try:
        for spec in args.source:
            path, kind = parse_source(spec)
            for i, piece in enumerate(pieces(path.read_text(encoding="utf-8", errors="replace"))):
                key = f"{path.name}#{i}"
                if key in done:
                    continue
                if time.monotonic() - started > args.time_budget:
                    print(f"paused: {len(done)} pieces done, {facts} facts, ${cost:.4f}")
                    return
                ref = SourceRef(kind=kind, source_id=path.stem, locator=f"part {i + 1}", observed_at=datetime.now(UTC))
                budget = settings.new_budget()
                result = learner.learn(
                    CaptureRequest(club_id=args.club, sources=[Untrusted(content=piece, source=ref)]),
                    date.today(),
                    budget,
                )
                cost += budget.spent_usd
                facts += len(result.proposals)
                dropped += result.sources_skipped
                done.append(key)
                state_path.write_text(
                    json.dumps({"done": done, "proposals": facts, "dropped": dropped, "cost": str(cost)})
                )
        print(f"all done: {len(done)} pieces, {facts} facts sent to Review, {dropped} dropped, ${cost:.4f}")
    finally:
        store.close()


def _card(p: KnowHowProposal, store: KnowHowStore) -> dict[str, str]:
    known = store.latest(p.target_item) if p.target_item else None
    src = p.candidate.sources[0] if p.candidate.sources else None
    warning = []
    if p.injection_flags:
        warning.append("source had hidden instructions: " + "; ".join(p.injection_flags))
    if "may be outdated" in p.rationale:
        warning.append("the source may be outdated")
    return {
        "proposal_id": p.proposal_id,
        "type": {
            "create": "new fact",
            "merge": "same as a known fact",
            "update": "newer version",
            "contradiction": "disagrees",
        }.get(p.op.value, p.op.value),
        "title": p.candidate.title,
        "statement": p.candidate.statement,
        "quote": (src.quote or "") if src else "",
        "source": f"{src.source_id} ({src.locator})" if src else "",
        "known_fact": known.statement if known else "",
        "warning": " | ".join(warning),
        "decision": "",
        "edited_text": "",
    }


def sheet(args: argparse.Namespace) -> None:
    store = KnowHowStore(open_club_store_backend(args.data_dir, args.club))
    try:
        cards = [_card(p, store) for p in store.pending.values() if p.candidate.club_id in (args.club, None)]
    finally:
        store.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(cards)
    print(f"{len(cards)} facts to review in {args.out}: write approve, reject or edit in 'decision'")


def apply(args: argparse.Namespace) -> None:
    members = MemberStore(args.data_dir)
    member = members.get(args.member)
    members.close()
    if member is None or member.club_id != args.club or not member.is_cabinet:
        raise SystemExit(f"{args.member} is not a cabinet member of {args.club}")
    store = KnowHowStore(open_club_store_backend(args.data_dir, args.club))
    done = skipped = 0
    try:
        with args.sheet.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                decision = row["decision"].strip().lower()
                proposal = store.pending.get(row["proposal_id"])
                if not decision or proposal is None:
                    skipped += 1
                    continue
                if decision not in {"approve", "reject", "edit"}:
                    raise SystemExit(
                        f"{row['proposal_id']}: decision must be approve, reject or edit, not {decision!r}"
                    )
                edited = None
                if decision == "edit":
                    if not row["edited_text"].strip():
                        raise SystemExit(f"{row['proposal_id']}: 'edit' needs the corrected text in edited_text")
                    edited = proposal.candidate.model_copy(update={"statement": row["edited_text"].strip()})
                verdict = {
                    "approve": VerifyDecision.ACCEPT,
                    "reject": VerifyDecision.REJECT,
                    "edit": VerifyDecision.ACCEPT_EDITED,
                }
                store.verify(
                    VerifyRequest(proposal=proposal, decision=verdict[decision], edited_candidate=edited),
                    member.actor(),
                    datetime.now(UTC),
                )
                done += 1
    finally:
        store.close()
    print(f"{done} decisions applied, {skipped} rows left undecided")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("learn", "sheet", "apply"):
        p = sub.add_parser(name)
        p.add_argument("--club", required=True)
        p.add_argument("--data-dir", type=Path, default=Path("data/app"))
        if name == "learn":
            p.add_argument("--source", action="append", required=True, metavar="FILE[:KIND]")
            p.add_argument(
                "--time-budget", type=float, default=float("inf"), help="stop after N seconds; rerun to resume"
            )
        if name == "sheet":
            p.add_argument("--out", type=Path, required=True)
        if name == "apply":
            p.add_argument("--sheet", type=Path, required=True)
            p.add_argument("--member", required=True, help="the cabinet member deciding (member id)")
    args = parser.parse_args()
    {"learn": learn, "sheet": sheet, "apply": apply}[args.command](args)


if __name__ == "__main__":
    main()
