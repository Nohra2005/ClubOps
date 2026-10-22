"""Show and check TASKS.md.

    python scripts/tasks.py                 # everyone's open tasks
    python scripts/tasks.py --who joey      # one person's list
    python scripts/tasks.py --check         # validate the file (used by make check)

A task is ready when everything it needs is done; it is waiting otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TASKS_FILE = Path(__file__).resolve().parent.parent / "TASKS.md"
OWNERS = ("tatiana", "christophe", "joey")
STATUSES = ("todo", "doing", "blocked", "review", "done")
PREFIX = {"tatiana": "T", "christophe": "C", "joey": "J"}

HEADING = re.compile(r"^### ([A-Z]-\d{2}) (.+)$")
FIELD = re.compile(r"^- (Owner|Status|Needs|What|Done when): (.*)$")


@dataclass
class Task:
    task_id: str
    title: str
    line: int
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def owner(self) -> str:
        return self.fields.get("Owner", "")

    @property
    def status(self) -> str:
        return self.fields.get("Status", "")

    @property
    def needs(self) -> list[str]:
        raw = self.fields.get("Needs", "none").strip()
        return [] if raw == "none" else [n.strip() for n in raw.split(",")]


def parse(text: str) -> list[Task]:
    tasks: list[Task] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if heading := HEADING.match(line):
            tasks.append(Task(heading.group(1), heading.group(2), number))
        elif tasks and (item := FIELD.match(line)):
            tasks[-1].fields[item.group(1)] = item.group(2).strip()
    return tasks


def problems(tasks: list[Task]) -> list[str]:
    found: list[str] = []
    ids = [t.task_id for t in tasks]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        found.append(f"{dup}: ID used more than once")
    known = set(ids)
    for t in tasks:
        where = f"{t.task_id} (line {t.line})"
        for name in ("Owner", "Status", "Needs", "What", "Done when"):
            if not t.fields.get(name):
                found.append(f"{where}: missing '{name}'")
        if t.owner and t.owner not in OWNERS:
            found.append(f"{where}: unknown owner '{t.owner}' (use one of {', '.join(OWNERS)})")
        elif t.owner and not t.task_id.startswith(PREFIX[t.owner] + "-"):
            found.append(f"{where}: {t.owner}'s tasks start with {PREFIX[t.owner]}-")
        if t.status and t.status not in STATUSES:
            found.append(f"{where}: unknown status '{t.status}' (use one of {', '.join(STATUSES)})")
        for need in t.needs:
            if need not in known:
                found.append(f"{where}: needs '{need}', which does not exist")
            elif need == t.task_id:
                found.append(f"{where}: needs itself")
    return found


def waiting_on(task: Task, by_id: dict[str, Task]) -> list[str]:
    return [n for n in task.needs if n in by_id and by_id[n].status != "done"]


def report(tasks: list[Task], who: str | None) -> str:
    by_id = {t.task_id: t for t in tasks}
    lines: list[str] = []
    for owner in OWNERS:
        if who and owner != who:
            continue
        mine = [t for t in tasks if t.owner == owner]
        open_ = [t for t in mine if t.status != "done"]
        done = len(mine) - len(open_)
        lines.append(f"\n{owner.capitalize()}: {done} of {len(mine)} done")
        for t in open_:
            wait = waiting_on(t, by_id)
            note = f"  waiting on {', '.join(wait)}" if wait and t.status != "blocked" else ""
            if not wait and t.status == "todo":
                note = "  ready to start"
            lines.append(f"  [{t.status:7}] {t.task_id} {t.title}{note}")
    return "\n".join(lines).lstrip("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--who", choices=OWNERS)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--file", type=Path, default=TASKS_FILE)
    args = parser.parse_args(argv)

    tasks = parse(args.file.read_text(encoding="utf-8"))
    errors = problems(tasks)
    if args.check:
        for error in errors:
            print(f"TASKS.md: {error}")
        if not tasks:
            print("TASKS.md: no tasks found")
            return 1
        return 1 if errors else 0
    if errors:
        print(f"Warning: TASKS.md has {len(errors)} problem(s); run with --check.", file=sys.stderr)
    print(report(tasks, args.who))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
