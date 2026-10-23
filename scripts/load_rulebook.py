"""Load the AUB rulebook into the shared store (general.db).

  uv run python scripts/load_rulebook.py --data-dir data/app --verified-by m-tatiana-nohra

The rules in the file are already verified (reviewed by a cabinet member, see build_rulebook.py).
--verified-by re-marks them with another reviewer, after a new review.
Loading twice updates a rule only when its text changed (a new version; the old one stays as history).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from clubops.contracts.knowhow import ItemStatus, KnowHowItem
from clubops.knowhow.backends import SqliteBackend

RULEBOOK = Path("data/rulebook/aub-rules.json")


def read_rulebook(path: Path = RULEBOOK) -> list[KnowHowItem]:
    return [KnowHowItem.model_validate(raw) for raw in json.loads(path.read_text())]


def load(data_dir: Path, verified_by: str | None, path: Path = RULEBOOK) -> tuple[int, int]:
    """Returns (added, updated)."""
    backend = SqliteBackend(data_dir / "general.db")
    added = updated = 0
    now = datetime.now(UTC)
    try:
        for listed in read_rulebook(path):
            rule = listed
            if verified_by:
                rule = KnowHowItem.model_validate(
                    {
                        **listed.model_dump(),
                        "status": ItemStatus.VERIFIED,
                        "verified_by": verified_by,
                        "verified_at": now,
                    }
                )
            old = backend.versions(rule.item_id)
            if not old:
                backend.append(rule)
                added += 1
                continue
            last = old[-1]
            same = last.model_dump(include={"title", "statement", "details", "status"}) == rule.model_dump(
                include={"title", "statement", "details", "status"}
            )
            if not same:
                backend.append(rule.model_copy(update={"version": last.version + 1, "supersedes": None}))
                updated += 1
    finally:
        backend.close()
    return added, updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/app"))
    parser.add_argument("--verified-by", default=None, help="member id of the cabinet member who reviewed them")
    args = parser.parse_args()
    added, updated = load(args.data_dir, args.verified_by)
    print(f"rulebook: {added} added, {updated} updated")


if __name__ == "__main__":
    main()
