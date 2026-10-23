"""Design-log and failure-matrix numbers are shared by the team: each is used once (AGENTS.md step 7)."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest


@pytest.mark.parametrize(("path", "prefix"), [("docs/design-log.md", "D"), ("docs/failure-matrix.md", "F")])
def test_every_number_is_used_once(path: str, prefix: str) -> None:
    numbers = re.findall(rf"^\| ({prefix}-\d+) \|", Path(path).read_text(), re.MULTILINE)
    assert numbers, f"no rows found in {path}"
    twice = sorted(n for n, count in Counter(numbers).items() if count > 1)
    assert not twice, f"used more than once in {path}: {twice}. Renumber your new rows (AGENTS.md step 7)."
