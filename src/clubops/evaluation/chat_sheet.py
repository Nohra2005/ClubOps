"""Marking sheet for the private chatbot test (J-17).

The chatbot's wording never matches a person's word for word, so the answers are not compared as text.
Step 1 (`ask`) asks every question and writes a sheet. A person marks each answered question yes / partly / no
and whether its sources fit. Step 2 (`score`) counts the sheet. What needs no person is filled in by code:
a "not sure" that was right, an invented answer, a missed answer.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from clubops.capabilities.runner import CapabilityError
from clubops.contracts.knowhow import Answer

COLUMNS = [
    "id",
    "question",
    "her_answer",
    "expected",
    "clubops_answer",
    "clubops_known",
    "clubops_sources",
    "cost_usd",
    "correct",
    "sources_ok",
]
KNOWN, NOT_SURE = "known", "not_sure"
MARKS = {"yes", "partly", "no"}


@dataclass(frozen=True)
class Question:
    q_id: str
    question: str
    expected: str  # "known" or "not_sure"
    answer: str


def read_questions(path: Path) -> list[Question]:
    """Read the private question file as it is: q_id, question, expected (known / not_sure), answer."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = [
            {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(stream)
        ]
    questions = [Question(r["q_id"], r["question"], r["expected"], r["answer"]) for r in rows]
    bad = [q.q_id for q in questions if q.expected not in {KNOWN, NOT_SURE}]
    if bad:
        raise ValueError(f"expected must be 'known' or 'not_sure' for: {', '.join(bad)}")
    return questions


def ask_sheet(
    questions: list[Question],
    answer: Callable[[str], tuple[Answer, Decimal, list[str]]],
) -> list[dict[str, str]]:
    """One row per question. `answer` returns the chatbot's Answer, its cost, and the titles of what it cited."""
    rows = []
    for q in questions:
        try:
            reply, cost, titles = answer(q.question)
        except CapabilityError as problem:  # one failed question must not lose the rest of the paid run (F-320)
            rows.append(_failed(q, problem.message))
            continue
        correct, sources_ok = "", ""
        if q.expected == NOT_SURE:
            correct, sources_ok = ("no", "n/a") if reply.known else ("yes", "n/a")
        elif not reply.known:
            correct, sources_ok = "no", "n/a"  # it should have answered and said "not sure"
        rows.append(
            {
                "id": q.q_id,
                "question": q.question,
                "her_answer": q.answer,
                "expected": q.expected,
                "clubops_answer": reply.text,
                "clubops_known": "yes" if reply.known else "no",
                "clubops_sources": "; ".join(titles),
                "cost_usd": f"{cost:.6f}",
                "correct": correct,
                "sources_ok": sources_ok,
            }
        )
    return rows


def _failed(q: Question, message: str) -> dict[str, str]:
    return {
        "id": q.q_id,
        "question": q.question,
        "her_answer": q.answer,
        "expected": q.expected,
        "clubops_answer": f"ERROR: {message}",
        "clubops_known": "error",
        "clubops_sources": "",
        "cost_usd": "0",
        "correct": "n/a",
        "sources_ok": "n/a",
    }


def write_sheet(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_sheet(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [
            {(k or "").strip(): (v or "").strip().lower() for k, v in row.items()} for row in csv.DictReader(stream)
        ]


def needs_marking(row: dict[str, str]) -> bool:
    return row["expected"] == KNOWN and row["clubops_known"] == "yes"


def unmarked(rows: list[dict[str, str]]) -> list[str]:
    """Ids still to mark: an answered question needs `correct` (yes / partly / no) and `sources_ok` (yes / no)."""
    return [
        r["id"]
        for r in rows
        if needs_marking(r) and (r["correct"] not in MARKS or r["sources_ok"] not in {"yes", "no"})
    ]


def score_sheet(rows: list[dict[str, str]]) -> dict[str, Decimal | int]:
    todo = unmarked(rows)
    if todo:
        raise ValueError(f"mark these first (correct: yes/partly/no, sources_ok: yes/no): {', '.join(todo)}")
    marked = [r for r in rows if needs_marking(r)]
    return {
        "questions": len(rows),
        "answered_correct": sum(r["correct"] == "yes" for r in marked),
        "answered_partly": sum(r["correct"] == "partly" for r in marked),
        "answered_wrong": sum(r["correct"] == "no" for r in marked),
        "missed": sum(r["expected"] == KNOWN and r["clubops_known"] == "no" for r in rows),
        "correct_not_sure": sum(r["expected"] == NOT_SURE and r["clubops_known"] == "no" for r in rows),
        "invented": sum(r["expected"] == NOT_SURE and r["clubops_known"] == "yes" for r in rows),
        "sources_ok": sum(r["sources_ok"] == "yes" for r in marked),
        "answered": len(marked),
        "errors": sum(r["clubops_known"] == "error" for r in rows),
        "cost_usd": sum((Decimal(r["cost_usd"] or "0") for r in rows), Decimal("0")),
    }


def table(result: dict[str, Decimal | int]) -> str:
    r = result
    return "\n".join(
        [
            "| Questions | Correct | Partly | Wrong | Missed (said not sure) | Correct not sure | Invented | "
            "Sources OK | Errors | Cost (USD) |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            f"| {r['questions']} | {r['answered_correct']} | {r['answered_partly']} | {r['answered_wrong']} | "
            f"{r['missed']} | {r['correct_not_sure']} | {r['invented']} | {r['sources_ok']} of {r['answered']} | "
            f"{r['errors']} | {Decimal(r['cost_usd']):.4f} |",
        ]
    )
