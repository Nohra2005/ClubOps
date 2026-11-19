"""Fetch forwarded OSA e-mails from the ClubOps Gmail inbox into each club's waiting queue.

Free: no model call. Reading an e-mail into Review cards is a separate, paid step a cabinet member
triggers (T-47). Prints counts only, never e-mail content.

    uv run python scripts/fetch_inbox.py --data-dir data/private/app
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from clubops.config import _read_dotenv
from clubops.gmail_access import GmailKeyError, access_token, cabinet_senders, parse_extra_senders
from clubops.inbox.capture import PendingInbox
from clubops.inbox.gmail import GmailGateway, fetch_into_queue


def main() -> int:
    values = {**_read_dotenv(Path(".env")), **os.environ}
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=Path(values.get("CLUBOPS_DATA_DIR") or "data/app"))
    args = parser.parse_args()

    try:
        token = access_token(
            values.get("CLUBOPS_GMAIL_CLIENT_ID"),
            values.get("CLUBOPS_GMAIL_CLIENT_SECRET"),
            values.get("CLUBOPS_GMAIL_REFRESH_TOKEN"),
        )
    except GmailKeyError as error:
        print(f"Gmail: {error}", file=sys.stderr)
        return 2

    senders = cabinet_senders(args.data_dir, parse_extra_senders(values.get("CLUBOPS_INBOX_SENDERS")))
    queue = PendingInbox(args.data_dir / "inbox.db")
    gateway = GmailGateway(token)
    listed = len(gateway.list_ids())
    added = fetch_into_queue(gateway, queue, senders, datetime.now(UTC))
    print(f"Gmail: {listed} e-mails in the inbox, {added} new ones queued.")
    for club_id in sorted(senders):
        waiting = len(queue.pending(club_id))
        if waiting:
            print(f"  {club_id}: {waiting} waiting to be read")
    if listed and not added:
        print(
            "  Nothing new queued. E-mails already queued are skipped; others were not forwarded by a known "
            "cabinet address to clubops.agent+<club>@gmail.com."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
