"""TASKS.md stays valid, and the checker catches the mistakes people make when editing it."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("tasks_script", ROOT / "scripts" / "tasks.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["tasks_script"] = module
    spec.loader.exec_module(module)
    return module


tasks = _load()

GOOD = """
### T-01 First
- Owner: tatiana
- Status: done
- Needs: none
- What: a
- Done when: b

### C-01 Second
- Owner: christophe
- Status: todo
- Needs: T-01
- What: a
- Done when: b

### J-01 Third
- Owner: joey
- Status: todo
- Needs: C-01
- What: a
- Done when: b
"""


def test_real_tasks_file_is_valid() -> None:
    parsed = tasks.parse((ROOT / "TASKS.md").read_text(encoding="utf-8"))
    assert parsed
    assert tasks.problems(parsed) == []


def test_good_file_has_no_problems_and_shows_readiness() -> None:
    parsed = tasks.parse(GOOD)
    assert tasks.problems(parsed) == []
    out = tasks.report(parsed, None)
    assert "C-01 Second  ready to start" in out
    assert "J-01 Third  waiting on C-01" in out
    assert "Tatiana: 1 of 1 done" in out


def test_report_for_one_person() -> None:
    out = tasks.report(tasks.parse(GOOD), "joey")
    assert "J-01" in out
    assert "C-01 Second" not in out


def test_catches_editing_mistakes() -> None:
    bad = GOOD.replace("Needs: T-01", "Needs: T-99").replace("Status: done", "Status: finished")
    bad = bad.replace("Owner: joey", "Owner: marc") + "\n### T-01 Duplicate\n- Owner: tatiana\n"
    found = "\n".join(tasks.problems(tasks.parse(bad)))
    assert "needs 'T-99', which does not exist" in found
    assert "unknown status 'finished'" in found
    assert "unknown owner 'marc'" in found
    assert "T-01: ID used more than once" in found
    assert "missing 'Status'" in found


def test_catches_wrong_prefix_and_self_need() -> None:
    bad = GOOD.replace("### C-01 Second", "### T-02 Second").replace("Needs: C-01", "Needs: J-01")
    found = "\n".join(tasks.problems(tasks.parse(bad)))
    assert "christophe's tasks start with C-" in found
    assert "needs itself" in found


def test_main_check_and_listing(tmp_path: Path, capsys: object) -> None:
    good = tmp_path / "TASKS.md"
    good.write_text(GOOD, encoding="utf-8")
    assert tasks.main(["--check", "--file", str(good)]) == 0
    assert tasks.main(["--who", "joey", "--file", str(good)]) == 0
    empty = tmp_path / "EMPTY.md"
    empty.write_text("nothing here", encoding="utf-8")
    assert tasks.main(["--check", "--file", str(empty)]) == 1
