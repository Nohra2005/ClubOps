"""A separate test copy of a club's store with the president's own stated facts loaded (J-17 test).

The chatbot test needs the club's facts in the store. The president's 22 Oct facts (F01..F35) were never
approved into the real store, and the real store must not change for a test, so the facts go into a copy.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from clubops.contracts.common import SourceKind, SourceRef
from clubops.contracts.knowhow import DecisionDetails, ItemStatus, KnowHowItem, Scope, Support
from clubops.knowhow.store import KnowHowStore

SEED_MEMBER = "m-eval-seed"


def read_facts(path: Path) -> list[dict[str, str]]:
    """Columns: fact_id, scope (aub / club / club?), statement, source. Extra columns are ignored."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [
            {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(stream)
        ]


def seed_facts(store: KnowHowStore, rows: list[dict[str, str]], club_id: str, now: datetime | None = None) -> int:
    """Add each row as a verified fact. A row whose id already exists is skipped. Returns how many were added."""
    stamp = now or datetime.now(UTC)
    added = 0
    for row in rows:
        item_id = f"kh-eval-{row['fact_id'].lower()}"
        if store.latest(item_id) is not None:
            continue
        aub = row["scope"] == "aub"
        statement = row["statement"]
        store.backend.append(
            KnowHowItem(
                item_id=item_id,
                scope=Scope.AUB if aub else Scope.CLUB,
                club_id=None if aub else club_id,
                title=statement[:100],
                statement=statement,
                details=DecisionDetails(
                    decision=statement[:300], rationale=f"Stated by the president: {row['source']}"
                ),
                sources=[
                    SourceRef(
                        kind=SourceKind.INTERVIEW,
                        source_id=f"president-{row['source'] or 'session'}"[:200],
                        quote=statement[:500],
                        observed_at=stamp,
                    )
                ],
                support=Support(source_count=1),
                status=ItemStatus.VERIFIED,
                version=1,
                verified_by=SEED_MEMBER,
                verified_at=stamp,
                last_confirmed_at=stamp,
            )
        )
        added += 1
    return added
