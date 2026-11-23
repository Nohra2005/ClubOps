"""Make one e-mail fetchable and readable again. Free. Shows what it would do; add --yes to do it.

    uv run python scripts/unread_inbox.py --data-dir data/private/app --message-id 1a1f326e22e384bf
    uv run python scripts/unread_inbox.py --data-dir data/private/app --message-id 1a1f326e22e384bf --yes

Then run scripts/fetch_inbox.py. Backups of the three inbox files go to <data-dir>/backups first.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from clubops.inbox_reset import forget_read


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--message-id", required=True)
    parser.add_argument("--yes", action="store_true", help="apply the change (default: show only)")
    args = parser.parse_args()
    for line in forget_read(args.data_dir, args.message_id, apply=args.yes):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
