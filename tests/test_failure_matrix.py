"""Keeps docs/failure-matrix.md honest: every covered row must point to a real test."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROW = re.compile(r"^\| (F-\d+) \|.*\| `?([^|`]*)`? \| ([^|]+) \|$")


def rows() -> list[tuple[str, str, str]]:
    found = []
    for line in Path("docs/failure-matrix.md").read_text().splitlines():
        m = ROW.match(line.strip())
        if m:
            found.append((m.group(1), m.group(2).strip(), m.group(3).strip()))
    return found


def test_matrix_has_rows_with_unique_ids() -> None:
    ids = [r[0] for r in rows()]
    assert len(ids) >= 30
    assert len(ids) == len(set(ids))


def test_covered_rows_point_to_existing_tests() -> None:
    missing = []
    for fid, ref, status in rows():
        if not status.startswith(("covered", "partial")):
            continue
        path, _, name = ref.partition("::")
        tree = ast.parse(Path(path).read_text()) if Path(path).exists() else None
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)} if tree else set()
        if name not in names:
            missing.append(f"{fid}: {ref}")
    assert not missing, f"failure-matrix rows without a real test: {missing}"
