"""Move a club's approved knowledge between two data folders (T-51): export on one computer, import on the host.

  # on your computer: the club's facts plus the AUB-wide facts, one private file (never commit it)
  uv run python scripts/move_knowledge.py export --club running-club \\
      --data-dir data/private/app --out data/private/running-club.jsonl

  # on the host (back up the data folder first). Add --dry-run to count without writing
  python scripts/move_knowledge.py import --club running-club \\
      --data-dir /var/data/clubops --file running-club.jsonl

Only adds items the target does not have yet (by id), keeps every version, never touches members or sign-in, never
overwrites. The import refuses a file holding another club's items. Rerunning is harmless."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `python scripts/move_knowledge.py` finds `clubops`

from clubops.contracts.knowhow import KnowHowItem, Scope
from clubops.knowhow.backends import open_club_store_backend


def belongs(item: KnowHowItem, club: str) -> bool:
    return item.scope is Scope.AUB or item.club_id == club


def export_items(club: str, data_dir: Path, out: Path) -> tuple[int, int]:
    """Write every version of every AUB-wide item and of the club's items. Returns (items, versions)."""
    backend = open_club_store_backend(data_dir, club)
    lines: list[str] = []
    ids = 0
    try:
        for latest in backend.latest_all():
            if not belongs(latest, club):
                continue
            ids += 1
            lines += [v.model_dump_json() for v in backend.versions(latest.item_id)]
    finally:
        backend.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ids, len(lines)


def import_items(club: str, data_dir: Path, file: Path, *, dry_run: bool = False) -> tuple[int, int]:
    """Add the items the target lacks. Returns (added, skipped as already there)."""
    versions: dict[str, list[KnowHowItem]] = {}
    for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = KnowHowItem.model_validate_json(line)
        if not belongs(item, club):
            raise SystemExit(f"line {number}: item belongs to another club; nothing was imported")
        versions.setdefault(item.item_id, []).append(item)
    backend = open_club_store_backend(data_dir, club)
    added = skipped = 0
    try:
        with backend.transaction():
            for item_id, history in versions.items():
                if backend.has(item_id):
                    skipped += 1
                    continue
                added += 1
                if not dry_run:
                    for version in sorted(history, key=lambda v: v.version):
                        backend.append(version)
    finally:
        backend.close()
    return added, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("export", "import"):
        p = sub.add_parser(name)
        p.add_argument("--club", required=True)
        p.add_argument("--data-dir", type=Path, required=True)
        if name == "export":
            p.add_argument("--out", type=Path, required=True)
        else:
            p.add_argument("--file", type=Path, required=True)
            p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "export":
        ids, count = export_items(args.club, args.data_dir, args.out)
        print(f"{ids} items ({count} versions) written to {args.out}. Private: never commit or paste it.")
    else:
        added, skipped = import_items(args.club, args.data_dir, args.file, dry_run=args.dry_run)
        print(f"{'would add' if args.dry_run else 'added'} {added} items, {skipped} already there")


if __name__ == "__main__":
    main()
