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
from clubops.inbox.gmail import GmailGateway
from clubops.inbox.guards import InboxLedger
from clubops.inbox_intake import InboxNotes, intake, parse_osa_senders


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
    osa = parse_osa_senders(values.get("CLUBOPS_OSA_SENDERS"))
    if not osa:
        print("Inbox: CLUBOPS_OSA_SENDERS is empty in .env, so every e-mail would be skipped.", file=sys.stderr)
        return 2
    queue = PendingInbox(args.data_dir / "inbox.db")
    notes = InboxNotes(args.data_dir / "inbox-notes.db")
    counts = intake(
        GmailGateway(token),
        queue,
        notes=notes,
        ledger=InboxLedger(args.data_dir / "inbox-ledger.db"),
        cabinet=senders,
        osa_senders=osa,
        received_at=datetime.now(UTC),
    )
    print(
        f"Gmail: {counts['queued']} new e-mails queued, {counts['skipped']} skipped with a reason, "
        f"{counts['not_for_a_club']} not forwarded by a known cabinet address to a club."
    )
    for club_id in sorted(senders):
        waiting, skipped = len(queue.pending(club_id)), notes.skipped(club_id)
        if waiting or skipped:
            print(f"  {club_id}: {waiting} waiting to be read, {len(skipped)} skipped")
            for row in skipped:
                print(f"    skipped: {row['why']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
