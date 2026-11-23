"""Let one e-mail be fetched and read again (F-244).

ClubOps reads an e-mail once. Sometimes that has to be undone: the cards were rejected by mistake, or the reader
was improved and the e-mail should be read again. This clears the "already read" marks for ONE e-mail so the next
free fetch queues it again from Gmail. It copies the three inbox files first and changes nothing unless told to.
Prints counts and ids only, never e-mail content.
"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

FILES = ("inbox.db", "inbox-notes.db", "inbox-ledger.db")


def forget_read(data_dir: Path, message_id: str, *, apply: bool, now: datetime | None = None) -> list[str]:
    """What would change (or did change, with ``apply``) so ``message_id`` is fetched and read again."""
    report: list[str] = []
    paths = {name: data_dir / name for name in FILES}
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        return [f"Not found in {data_dir}: {', '.join(missing)}. Nothing changed."]
    with closing(sqlite3.connect(paths["inbox-notes.db"])) as notes:
        row = notes.execute("SELECT fingerprint FROM accepted WHERE message_id=?", (message_id,)).fetchone()
    if row is None:
        return [f"E-mail {message_id} was never accepted for reading here. Nothing changed."]
    fingerprint = str(row[0])
    with closing(sqlite3.connect(paths["inbox-ledger.db"])) as ledger:
        marked = ledger.execute("SELECT state FROM read_mail WHERE fingerprint=?", (fingerprint,)).fetchone()
    with closing(sqlite3.connect(paths["inbox.db"])) as queue:
        queued = queue.execute("SELECT processed FROM inbox_capture WHERE message_id=?", (message_id,)).fetchone()
    report += [
        f"E-mail {message_id}: read mark {'yes (' + str(marked[0]) + ')' if marked else 'none'}, "
        f"queue entry {'yes' if queued else 'none'}, notes entry yes.",
    ]
    if not apply:
        return [*report, "Dry run: nothing changed. Add --yes to apply."]
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    backup = data_dir / "backups" / f"unread-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    for name, path in paths.items():
        shutil.copy2(path, backup / name)
    report.append(f"Backups of the three files are in {backup}.")
    with closing(sqlite3.connect(paths["inbox-ledger.db"])) as ledger, ledger:
        ledger.execute("DELETE FROM read_mail WHERE fingerprint=?", (fingerprint,))
    with closing(sqlite3.connect(paths["inbox.db"])) as queue, queue:
        queue.execute("DELETE FROM inbox_capture WHERE message_id=?", (message_id,))
    with closing(sqlite3.connect(paths["inbox-notes.db"])) as notes, notes:
        notes.execute("DELETE FROM accepted WHERE message_id=?", (message_id,))
    report.append("Cleared. Run the free fetch now: the e-mail comes back as waiting.")
    return report
