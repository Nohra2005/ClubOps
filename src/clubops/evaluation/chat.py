"""Replayable scoring for cited chatbot answers (J-17)."""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from clubops.contracts.knowhow import Answer, AskRequest


@dataclass(frozen=True)
class ChatCase:
    case_id: str
    request: AskRequest
    expected_answer: str | None
    supporting_ids: frozenset[str]


@dataclass
class ChatScore:
    total: int = 0
    correct_answers: int = 0
    invented_answers: int = 0
    correct_unknowns: int = 0
    unsupported_citations: int = 0
    cost_usd: Decimal = Decimal("0")
    rows: list[dict[str, str]] = field(default_factory=list)


def load_cases(path: Path, club_id: str, as_of: date) -> list[ChatCase]:
    """Read a redacted CSV: id, question, expected_answer, supporting_ids.

    A blank expected_answer means the correct response is unknown. Supporting IDs are
    semicolon-separated verified know-how IDs; no private answer text is logged.
    """
    cases = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            expected = (row["expected_answer"] or "").strip()
            cases.append(
                ChatCase(
                    case_id=row["id"],
                    request=AskRequest(club_id=club_id, question=row["question"], as_of=as_of),
                    expected_answer=expected or None,
                    supporting_ids=frozenset(x.strip() for x in row["supporting_ids"].split(";") if x.strip()),
                )
            )
    return cases


def score(cases: list[ChatCase], predict: Callable[[AskRequest], tuple[Answer, Decimal]]) -> ChatScore:
    """Score each answer and its supporting citations with an injected predictor.

    ``predict`` returns (Answer, cost in USD). An injected predictor keeps tests in
    replay/fake mode; the CLI supplies the real model client in replay mode.
    """
    result = ChatScore()
    for case in cases:
        answer, cost = predict(case.request)
        expected_known = case.expected_answer is not None
        correct_answer = bool(
            expected_known
            and answer.known
            and " ".join(answer.text.casefold().split()) == " ".join((case.expected_answer or "").casefold().split())
        )
        correct_unknown = not expected_known and not answer.known
        invented = not expected_known and answer.known
        supported = not answer.known or (bool(answer.citations) and set(answer.citations) <= case.supporting_ids)
        result.total += 1
        result.correct_answers += correct_answer
        result.correct_unknowns += correct_unknown
        result.invented_answers += invented
        result.unsupported_citations += not supported
        result.cost_usd += cost
        result.rows.append(
            {
                "id": case.case_id,
                "correct_answer": str(correct_answer),
                "correct_unknown": str(correct_unknown),
                "invented": str(invented),
                "citations_supported": str(supported),
            }
        )
    return result


def table(result: ChatScore) -> str:
    return "\n".join(
        [
            "| Questions | Correct answers | Invented answers | Correct unknowns | "
            "Unsupported citations | Cost (USD) |",
            "|---:|---:|---:|---:|---:|---:|",
            f"| {result.total} | {result.correct_answers} | {result.invented_answers} | "
            f"{result.correct_unknowns} | {result.unsupported_citations} | {result.cost_usd:.4f} |",
        ]
    )
