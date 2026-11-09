"""ClubOps' prompts must fit any AUB club (D-91): none may name a club, a sport or a club's own places.

The prompts were written and tuned while testing on one club's events. This test keeps them general:
every system prompt in the app (the evaluation baselines are not part of the app) is read from the code
and checked for words that would quietly fit them to one kind of club."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "clubops"
CLUB_SPECIFIC = re.compile(
    r"\b(runs?|runners?|running|marathons?|triathlons?|races?|jog\w*|[0-9]+ ?k|swim\w*|cycl\w*|asme"
    r"|chess|debate|robotics|engineering society|green field|charity run)\b",
    re.IGNORECASE,
)


def _text(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(_text(v) for v in node.values)
    if isinstance(node, ast.BinOp):
        return _text(node.left) + _text(node.right)
    return ""


def prompts() -> list[tuple[str, str]]:
    """Every string assigned to a *SYSTEM* / *PROMPT* name or passed as ``system=``, outside evaluation/."""
    found: list[tuple[str, str]] = []
    for path in sorted(SRC.rglob("*.py")):
        if "evaluation" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and re.search(r"SYSTEM|PROMPT$", t.id) for t in node.targets
            ):
                found.append((f"{path.name}:{node.lineno}", _text(node.value)))
            if isinstance(node, ast.keyword) and node.arg == "system":
                found.append((f"{path.name}:{node.value.lineno}", _text(node.value)))
    return [(where, text) for where, text in found if text]


def test_the_app_prompts_are_found() -> None:
    names = {where.split(":")[0] for where, _ in prompts()}
    assert {"planner.py", "rules_judge.py", "capture.py", "ask.py"} <= names


@pytest.mark.parametrize(("where", "text"), prompts(), ids=[w for w, _ in prompts()])
def test_no_prompt_is_fitted_to_one_club(where: str, text: str) -> None:
    hits = sorted({m.group(0).lower() for m in CLUB_SPECIFIC.finditer(text)})
    assert not hits, f"{where} names {hits}: write it for any AUB club"


def test_the_check_catches_a_club_fitted_prompt() -> None:
    assert CLUB_SPECIFIC.search("Plan the fun run on Green Field") is not None
    assert CLUB_SPECIFIC.search("Plan the event and check the AUB rules") is None
