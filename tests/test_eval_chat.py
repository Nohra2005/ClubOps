"""Synthetic chatbot evaluation; no model key or private question file."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from scripts.eval_chat import main

from clubops.contracts.knowhow import Answer, AskRequest
from clubops.evaluation.chat import ChatCase, load_cases, score, table


def case(case_id: str, expected: str | None, sources: frozenset[str] = frozenset()) -> ChatCase:
    return ChatCase(
        case_id,
        AskRequest(club_id="math-club", question="Who books the room?", as_of=date(2026, 10, 31)),
        expected,
        sources,
    )


def test_score_reports_answer_unknown_invention_and_citation_errors() -> None:
    cases = [
        case("Q1", "Ask the events officer.", frozenset({"kh-room"})),
        case("Q2", None),
        case("Q3", None),
        case("Q4", "Ask the president.", frozenset({"kh-president"})),
    ]
    answers = iter(
        [
            Answer(known=True, text="Ask the events officer.", citations=["kh-room"], basis="verified"),
            Answer(known=False, text="I don't know.", basis="none", ask={"who": "President"}),
            Answer(known=True, text="Made up.", citations=["kh-room"], basis="verified"),
            Answer(known=True, text="Ask the president.", citations=["kh-unseen"], basis="verified"),
        ]
    )
    result = score(cases, lambda _: (next(answers), Decimal("0.001")))
    assert result.total == 4
    assert result.correct_answers == 2
    assert result.correct_unknowns == 1
    assert result.invented_answers == 1
    assert result.unsupported_citations == 2
    assert result.cost_usd == Decimal("0.004")
    assert "| 4 | 2 | 1 | 1 | 2 | 0.0040 |" in table(result)


def test_csv_loader_keeps_unknowns_and_supporting_ids(tmp_path: Path) -> None:
    path = tmp_path / "questions.csv"
    path.write_text(
        "id,question,expected_answer,supporting_ids\n"
        "Q1,Who books the room?,Ask the events officer.,kh-room;kh-policy\n"
        "Q2,Who has the key?,,\n",
        encoding="utf-8",
    )
    cases = load_cases(path, "math-club", date(2026, 10, 31))
    assert len(cases) == 2
    assert cases[0].supporting_ids == frozenset({"kh-room", "kh-policy"})
    assert cases[1].expected_answer is None


def test_cli_scores_an_unknown_question_in_replay_mode(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "questions.csv"
    path.write_text(
        "id,question,expected_answer,supporting_ids\nQ1,Xylophone?,,\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLUBOPS_MODEL_MODE", "replay")
    monkeypatch.setattr("sys.argv", ["eval_chat.py", "--cases", str(path), "--as-of", "2026-10-31"])
    main()
    assert "| 1 | 0 | 0 | 1 | 0 | 0.0000 |" in capsys.readouterr().out
