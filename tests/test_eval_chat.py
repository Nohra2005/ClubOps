"""Synthetic chatbot evaluation; no model key or private question file."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from scripts.eval_chat import main

from clubops.capabilities.runner import CapabilityError
from clubops.contracts.common import ErrorCode
from clubops.contracts.knowhow import Answer, AskRequest
from clubops.evaluation.chat import ChatCase, load_cases, score, table
from clubops.evaluation.chat_sheet import ask_sheet, read_questions, read_sheet, score_sheet, unmarked
from clubops.evaluation.chat_sheet import table as sheet_table


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


QUESTIONS = (
    "q_id,question,expected,answer,source,ask_who,look_in\n"
    "Q1,Who books the room?,known,Ask the events officer.,doc,,\n"
    "Q2,What is the food ceiling?,not_sure,Not known.,,OSA,forms\n"
    "Q3,Who has the key?,not_sure,Not known.,,Security,\n"
    "Q4,How early do we file?,known,Two weeks.,doc,,\n"
)


def fake_answers() -> object:
    replies = {
        "Who books the room?": Answer(known=True, text="The events officer.", citations=["kh-room"], basis="verified"),
        "What is the food ceiling?": Answer(known=False, text="Not sure.", basis="none", ask={"who": "OSA"}),
        "Who has the key?": Answer(known=True, text="Security.", citations=["kh-key"], basis="verified"),
        "How early do we file?": Answer(known=False, text="Not sure.", basis="none", ask={"who": "OSA"}),
    }
    return lambda text: (replies[text], Decimal("0.01"), ["Room rule"] if replies[text].known else [])


def test_the_sheet_fills_what_code_can_decide_and_leaves_the_rest_to_a_person(tmp_path: Path) -> None:
    """F-318: the exact-text match marked almost every answer wrong; a person marks, code counts."""
    path = tmp_path / "q.csv"
    path.write_text(QUESTIONS, encoding="utf-8-sig")  # the private file may start with a BOM
    rows = ask_sheet(read_questions(path), fake_answers())  # type: ignore[arg-type]
    by_id = {r["id"]: r for r in rows}
    assert by_id["Q1"]["correct"] == "" and by_id["Q1"]["her_answer"] == "Ask the events officer."
    assert by_id["Q2"]["correct"] == "yes"  # right "not sure"
    assert by_id["Q3"]["correct"] == "no"  # invented answer
    assert by_id["Q4"]["correct"] == "no"  # missed: it should have answered
    assert unmarked(rows) == ["Q1"]
    with pytest.raises(ValueError, match="Q1"):
        score_sheet(rows)
    by_id["Q1"].update(correct="partly", sources_ok="yes")
    result = score_sheet(rows)
    assert (result["answered_partly"], result["missed"], result["correct_not_sure"], result["invented"]) == (1, 1, 1, 1)
    assert result["cost_usd"] == Decimal("0.04")
    assert "| 4 | 0 | 1 | 0 | 1 | 1 | 1 | 1 of 1 | 0 | 0.0400 |" in sheet_table(result)


def test_cli_asks_unknown_questions_then_scores_the_sheet(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "q.csv"
    path.write_text("q_id,question,expected,answer\nQ1,Xylophone?,not_sure,Not known.\n", encoding="utf-8")
    sheet = tmp_path / "out" / "sheet.csv"
    monkeypatch.setenv("CLUBOPS_MODEL_MODE", "replay")
    monkeypatch.setattr(
        "sys.argv",
        [
            "eval_chat.py",
            "ask",
            "--cases",
            str(path),
            "--out",
            str(sheet),
            "--as-of",
            "2026-11-24",
            "--data-dir",
            str(tmp_path / "d"),
        ],
    )
    main()
    assert read_sheet(sheet)[0]["correct"] == "yes"
    monkeypatch.setattr("sys.argv", ["eval_chat.py", "score", "--sheet", str(sheet)])
    main()
    assert "| 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 of 0 | 0 | 0.0000 |" in capsys.readouterr().out


def test_the_sheet_is_refused_inside_the_repository(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "q.csv"
    path.write_text("q_id,question,expected,answer\nQ1,Xylophone?,not_sure,Not known.\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv", ["eval_chat.py", "ask", "--cases", str(path), "--out", "private-sheet.csv", "--as-of", "2026-11-24"]
    )
    with pytest.raises(SystemExit, match="outside the ClubOps folder"):
        main()


def test_a_failed_question_is_recorded_and_the_run_goes_on(tmp_path: Path) -> None:
    """F-320: one cut-off answer stopped the whole paid run and lost every answer already bought."""
    path = tmp_path / "q.csv"
    path.write_text(QUESTIONS, encoding="utf-8")
    good = fake_answers()

    def flaky(text: str) -> object:
        if text == "Who has the key?":
            raise CapabilityError(ErrorCode.INVALID_INPUT, "the model's answer was cut off")
        return good(text)  # type: ignore[operator]

    rows = ask_sheet(read_questions(path), flaky)  # type: ignore[arg-type]
    failed = next(r for r in rows if r["id"] == "Q3")
    assert len(rows) == 4 and failed["clubops_known"] == "error" and failed["clubops_answer"].startswith("ERROR:")
    assert unmarked(rows) == ["Q1"]  # an error needs no marking and is not counted as a right "not sure"
    rows[0].update(correct="yes", sources_ok="yes")
    result = score_sheet(rows)
    assert result["errors"] == 1 and result["correct_not_sure"] == 1 and result["invented"] == 0


def test_counts_need_no_marking(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "q.csv"
    path.write_text(QUESTIONS, encoding="utf-8")
    sheet = tmp_path / "sheet.csv"
    from clubops.evaluation.chat_sheet import write_sheet

    write_sheet(sheet, ask_sheet(read_questions(path), fake_answers()))  # type: ignore[arg-type]
    monkeypatch.setattr("sys.argv", ["eval_chat.py", "score", "--sheet", str(sheet), "--counts"])
    main()
    out = capsys.readouterr().out
    assert "expected known: 2 questions; answered 1, said not sure 1, errors 0" in out
    assert "expected not_sure: 2 questions; answered 1, said not sure 1, errors 0" in out


def test_search_check_is_free_and_reports_questions_with_no_facts(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "q.csv"
    path.write_text("q_id,question,expected,answer\nQ1,Xylophone?,not_sure,Not known.\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["eval_chat.py", "search", "--cases", str(path), "--as-of", "2026-11-24", "--data-dir", str(tmp_path / "d")],
    )
    main()
    out = capsys.readouterr().out
    assert "Q1 (not_sure): 0 facts found, 0 from the club" in out and "Questions with no facts found: 1 (Q1)" in out


def test_a_test_copy_gets_the_presidents_facts_and_the_real_store_is_untouched(tmp_path: Path) -> None:
    from clubops.evaluation.eval_store import read_facts, seed_facts
    from clubops.knowhow.backends import open_club_store_backend
    from clubops.knowhow.store import KnowHowStore
    from tests.factories import CLUB

    path = tmp_path / "facts.csv"
    path.write_text(
        "fact_id,scope,learned_from_event,statement,source\n"
        'F1,club?,E1,"Weekly runs are covered by one proposal per semester.",Synthetic\n'
        'F2,aub,,"The pool is free for all students.",Synthetic\n',
        encoding="utf-8-sig",
    )
    real = KnowHowStore(open_club_store_backend(tmp_path / "real", CLUB))
    copy = KnowHowStore(open_club_store_backend(tmp_path / "copy", CLUB))
    assert seed_facts(copy, read_facts(path), CLUB) == 2
    assert seed_facts(copy, read_facts(path), CLUB) == 0  # running it twice adds nothing
    found = [i.statement for i in copy.search(CLUB, "Is the pool free?")]
    assert any("pool is free" in s for s in found)
    assert real.search(CLUB, "Is the pool free?") == []
    copy.close()
    real.close()


def test_a_question_can_be_left_out_of_the_count_and_a_fact_left_out_of_the_copy(tmp_path: Path) -> None:
    from clubops.evaluation.eval_store import read_facts, seed_facts
    from clubops.knowhow.backends import open_club_store_backend
    from clubops.knowhow.store import KnowHowStore
    from tests.factories import CLUB

    path = tmp_path / "q.csv"
    path.write_text(QUESTIONS, encoding="utf-8")
    rows = ask_sheet(read_questions(path), fake_answers())  # type: ignore[arg-type]
    rows[0].update(correct="yes", sources_ok="yes")
    result = score_sheet(rows, frozenset({"Q3"}))  # Q3 was the invented answer
    assert result["questions"] == 3 and result["invented"] == 0
    facts = tmp_path / "facts.csv"
    facts.write_text(
        "fact_id,scope,statement,source\n"
        "F1,aub,The pool is free for all students.,S\n"
        "F2,aub,Civil Defense is needed.,S\n",
        encoding="utf-8",
    )
    copy = KnowHowStore(open_club_store_backend(tmp_path / "copy", CLUB))
    assert seed_facts(copy, read_facts(facts), CLUB, skip=frozenset({"F2"})) == 1
    assert copy.search(CLUB, "Civil Defense") == []
    copy.close()
