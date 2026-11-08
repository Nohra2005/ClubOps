"""The learning phase (T-09): read a club's material the normal way, then review what was learned.

ClubOps reads each file in pieces (the same learning code the app uses), and every fact it finds waits in
Review. The president then decides on a sheet instead of clicking through the app:

  # 1. learn (can be stopped and resumed; finished pieces are skipped)
  uv run python scripts/seed_club.py learn --club running-club --data-dir data/app \\
      --source data/private/club/cabinet.txt:chat_message --source data/private/club/bookings.txt:document

  # 2. write the review sheet, fill the "decision" column (approve / reject / edit + corrected text);
  #    "share_with_all_clubs" is yes for facts true for every AUB club (change it if ClubOps guessed wrong)
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
import re
import sys
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `python scripts/seed_club.py` finds `scripts`

from clubops.api.security import MemberStore
from clubops.config import Settings, load_settings
from clubops.contracts.common import SourceKind, SourceRef, Untrusted
from clubops.contracts.knowhow import CaptureRequest, Kind, KnowHowProposal, Scope, VerifyDecision, VerifyRequest
from clubops.evaluation.tracking import file_hash, tracker
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore, rescoped
from clubops.learning.capture import EXTRACT_VERSION, MATCH_VERSION, MAX_SOURCE_CHARS, Learner
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
    "share_with_all_clubs",
    "decision",
    "edited_text",
]


# A heading starts a new section: "ARTICLE IV", "Section 3", "3. Membership", "## Title".
_HEADING = re.compile(r"^\s*(?:#{1,6}\s|(?:article|section)\s+[ivxlc\d]+\b|\d{1,2}[.)]\s+\S)", re.IGNORECASE)


def _tail(out: list[str], rest: str) -> None:
    """Keep what is left over: on its own if it says anything, else joined to the piece before it, so that
    the pieces always add back up to the whole text."""
    if rest.strip():
        out.append(rest)
    elif rest and out:
        out[-1] += rest


def _by_lines(text: str, size: int) -> list[str]:
    """Pack whole lines into pieces of at most ``size`` characters (a longer single line is cut)."""
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
    _tail(out, current)
    return out


def sections(text: str) -> list[str]:
    """The document's own sections: a new one starts at each heading line. A chat has no headings, so it
    comes back whole and is split by line instead."""
    out: list[str] = []
    current = ""
    for raw in text.splitlines(keepends=True):
        if _HEADING.match(raw) and current.strip():
            out.append(current)
            current = ""
        current += raw
    _tail(out, current)
    return out


def pieces(text: str, size: int = MAX_SOURCE_CHARS) -> list[str]:
    """Split into pieces of at most ``size`` characters, on the document's own headings where it has them.

    A rule cut in half is a rule lost, so a section is kept whole wherever it fits (LMDX, arXiv 2309.10952,
    chunks on boundaries that entities rarely cross); a section too long for one piece is split by line.
    """
    out: list[str] = []
    current = ""
    for part in sections(text):
        if len(current) + len(part) > size:
            if len(part) > size:  # the section alone does not fit, so this one is split by line
                out.extend(_by_lines(current + part, size))
                current = ""
                continue
            if current.strip():
                out.append(current)
                current = ""
        current += part
    _tail(out, current)
    return out


_WA_LINE = re.compile(r"^\u200e?\[\d{1,2}/\d{1,2}/\d{2,4}, [^\]]+\] [^:]+: (.*)$")
_WA_NOISE = re.compile(
    r"joined using|requested to (join|add)|\badded\b|\bleft$|\bremoved\b|changed (this group|the group|their phone)"
    r"|(image|video|audio|sticker|GIF|document) omitted|This message was deleted|You deleted this message"
    r"|end-to-end encrypted|pinned a message|created group|changed the settings|turned (on|off) admin"
    r"|created the username|^POLL:$"
)


def clean_whatsapp(text: str) -> str:
    """Drop WhatsApp system lines (joins, adds, media placeholders...): they hold no know-how and cost money."""
    kept = []
    for line in text.splitlines():
        m = _WA_LINE.match(line)
        body = (m.group(1) if m else line).replace("\u200e", "").strip()
        if m and (not body or _WA_NOISE.search(body)):
            continue
        kept.append(line)
    return "\n".join(kept) + "\n"


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
    before = (len(done), facts, dropped, cost)
    unread = 0  # pieces the model could not be read for: not marked done, so a rerun retries them (F-168)
    try:
        for spec in args.source:
            path, kind = parse_source(spec)
            text = path.read_text(encoding="utf-8", errors="replace")
            if kind is SourceKind.CHAT_MESSAGE:
                text = clean_whatsapp(text)
            for i, piece in enumerate(pieces(text, args.piece_chars)):
                key = f"{path.name}#{i}"
                if key in done:
                    continue
                if time.monotonic() - started > args.time_budget:
                    print(f"paused: {len(done)} pieces done, {facts} facts, ${cost:.4f}")
                    _log_learning(
                        args, settings, before, (len(done), facts, dropped, cost), started=started, status="paused"
                    )
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
                if result.sources_failed:  # leave it out of ``done`` so a rerun retries it
                    unread += 1
                    print(f"could not read {key}: nothing learned from it")
                else:
                    done.append(key)
                state_path.write_text(
                    json.dumps({"done": done, "proposals": facts, "dropped": dropped, "cost": str(cost)})
                )
        note = f", {unread} pieces unread (rerun to retry, --piece-chars smaller if it repeats)" if unread else ""
        print(f"all done: {len(done)} pieces, {facts} facts sent to Review, {dropped} dropped, ${cost:.4f}{note}")
        _log_learning(args, settings, before, (len(done), facts, dropped, cost), started=started, status="done")
    finally:
        store.close()


def _log_learning(
    args: argparse.Namespace,
    settings: Settings,
    before: tuple[int, int, int, Decimal],
    after: tuple[int, int, int, Decimal],
    *,
    started: float,
    status: str,
) -> None:
    """One MLflow run per learn command (``--track``): what this chunk read and what it cost (D-94).
    Counts and costs only, never club text. Totals so far are logged too, for the onboarding curve."""
    track = tracker(getattr(args, "track", None))
    pieces_now = after[0] - before[0]
    facts_now, cost_now = after[1] - before[1], after[3] - before[3]
    params = {
        "club": args.club,
        "model": settings.model or "unset",
        "extract_version": EXTRACT_VERSION,
        "match_version": MATCH_VERSION,
        "mode": settings.mode.value,
        "sources": ",".join(parse_source(s)[0].name for s in args.source),
        "sources_sha": ",".join(file_hash(parse_source(s)[0]) for s in args.source),
        "status": status,
    }
    metrics = {
        "pieces": pieces_now,
        "facts": facts_now,
        "dropped": after[2] - before[2],
        "cost_usd": float(cost_now),
        "cost_per_piece_usd": float(cost_now) / max(pieces_now, 1),
        "cost_per_fact_usd": float(cost_now) / max(facts_now, 1),
        "seconds": time.monotonic() - started,
        "total_pieces": after[0],
        "total_facts": after[1],
        "total_cost_usd": float(after[3]),
    }
    tags = dict(t.split("=", 1) for t in getattr(args, "tag", []) or [])
    track.log_run(f"learn {args.club}", params, metrics, {"kind": "learning", **tags}, {})


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
        "share_with_all_clubs": "yes" if p.candidate.scope is Scope.AUB else "no",
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
                share = (row.get("share_with_all_clubs") or "").strip().lower()
                if share in {"yes", "no"} and decision != "reject":
                    if share == "no" and proposal.candidate.kind is Kind.RULE:
                        raise SystemExit(f"{row['proposal_id']}: AUB rules are always shared with every club")
                    moved = rescoped(edited or proposal.candidate, args.club, shared=share == "yes")
                    edited = None if moved == proposal.candidate else moved
                    if edited is not None and decision == "approve":
                        decision = "edit"  # only the sharing changed
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
            p.add_argument(
                "--piece-chars",
                type=int,
                default=MAX_SOURCE_CHARS,
                help="characters per piece; lower it for a rule-dense document whose answers are cut off",
            )
            p.add_argument("--track", metavar="EXPERIMENT", default=None, help="log cost and counts to MLflow")
            p.add_argument("--tag", action="append", default=[], metavar="KEY=VALUE", help="e.g. step=2")
        if name == "sheet":
            p.add_argument("--out", type=Path, required=True)
        if name == "apply":
            p.add_argument("--sheet", type=Path, required=True)
            p.add_argument("--member", required=True, help="the cabinet member deciding (member id)")
    args = parser.parse_args()
    {"learn": learn, "sheet": sheet, "apply": apply}[args.command](args)


if __name__ == "__main__":
    main()
