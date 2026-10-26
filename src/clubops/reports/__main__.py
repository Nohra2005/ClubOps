"""Usage: python -m clubops.reports --club running-club --month 2026-10 --output results/usage.json"""

import argparse
import json
from pathlib import Path

from clubops.reports.usage import build_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a metadata-only club usage report.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/app"))
    parser.add_argument("--club", required=True)
    parser.add_argument("--month", required=True, help="YYYY-MM, in Asia/Beirut")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build_report(args.data_dir, args.club, args.month)
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
