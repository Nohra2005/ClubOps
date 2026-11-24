"""Make a test copy of the club's data folder and load the president's stated facts into it (J-17 test).

    python scripts/make_eval_store.py --source data\\private\\app --facts data\\private\\d5\\facts-learned.csv
                                      --out data\\private\\app-eval

The real folder is never changed. The copy must go under data/private (not committed). Then run the chatbot test
with `--data-dir data\\private\\app-eval`. In the report, say that these facts were added to the test copy.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clubops.evaluation.eval_store import read_facts, seed_facts
from clubops.knowhow.backends import open_club_store_backend
from clubops.knowhow.store import KnowHowStore

PRIVATE = Path(__file__).resolve().parents[1] / "data" / "private"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--facts", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--club", default="running-club")
    args = parser.parse_args()
    out = args.out.resolve()
    if PRIVATE.resolve() not in out.parents:
        raise SystemExit("The copy holds private facts: put it under data/private.")
    if out.exists():
        raise SystemExit(f"{out} already exists. Choose a new folder or delete it first.")
    shutil.copytree(args.source, out)
    store = KnowHowStore(open_club_store_backend(out, args.club))
    try:
        added = seed_facts(store, read_facts(args.facts), args.club)
    finally:
        store.close()
    print(f"Copied {args.source.resolve()} to {out}\nFacts added to the copy: {added}")


if __name__ == "__main__":
    main()
