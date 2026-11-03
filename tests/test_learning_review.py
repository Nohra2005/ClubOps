"""Synthetic human labels exercise collection/grading; they are not real evaluation results."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

import pytest

from clubops.contracts.knowhow import Answer
from clubops.evaluation.learning import (
    REVIEW_COLUMNS,
    Case,
    Trial,
    human_markdown,
    summarize_ratings,
    write_review,
)
from tests.factories import CLUB, TODAY, item, verified


def example(number: int = 1) -> tuple[Case, Trial]:
    case = Case(
        f"case-{number:04d}",
        "PRIVATE SOURCE",
        "PRIVATE QUESTION: how do we reserve the synthetic studio?",
        (("Reserve the synthetic studio with form A.",),),
        club_id=CLUB,
        case_id=f"private-{number:03d}",
    )
    fact = verified(item(f"kh-synthetic-{number}", statement="Use form A to book the synthetic studio."))
    trial = Trial(
        approved=(fact,),
        before=Answer(known=False, text="Unknown", basis="none", ask={"who": "Synthetic reviewer"}),
        after=Answer(
            known=True, text="PRIVATE ANSWER: complete form A to book it.", basis="verified", citations=[fact.item_id]
        ),
        cost_usd=Decimal("0.01"),
    )
    return case, trial


def bundle(tmp_path: Path, count: int = 1) -> tuple[Path, Path]:
    cases, trials = zip(*(example(index) for index in range(1, count + 1)), strict=True)
    sheet, manifest = tmp_path / "review.csv", tmp_path / "review.run.json"
    write_review(cases, trials, TODAY, sheet=sheet, manifest=manifest, metadata={"dataset_kind": "synthetic"})
    return sheet, manifest


def read(sheet: Path) -> list[list[str]]:
    with sheet.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.reader(source))


def save(sheet: Path, rows: list[list[str]]) -> None:
    with sheet.open("w", encoding="utf-8-sig", newline="") as output:
        csv.writer(output).writerows(rows)


def rate(sheet: Path, grades: list[tuple[str, str]]) -> None:
    rows = read(sheet)
    for row, values in zip(rows[1:], grades, strict=True):
        row[5:] = values
    save(sheet, rows)


def test_review_exports_the_requested_columns_actual_paraphrase_and_blank_ratings(tmp_path: Path) -> None:
    sheet, manifest = bundle(tmp_path)
    header, row = read(sheet)
    assert header == list(REVIEW_COLUMNS)
    assert row == [
        "private-001",
        "Reserve the synthetic studio with form A.",
        "Use form A to book the synthetic studio.",
        "PRIVATE QUESTION: how do we reserve the synthetic studio?",
        "PRIVATE ANSWER: complete form A to book it.",
        "",
        "",
    ]
    # Private evidence is deliberately only in the requested sheet, not duplicated in run metadata.
    assert "PRIVATE" not in manifest.read_text() and "Use form A" not in manifest.read_text()
    with pytest.raises(ValueError, match="Fill learned and answer_ok"):
        summarize_ratings(sheet.read_bytes(), manifest.read_bytes())


def test_human_yes_accepts_a_paraphrase_without_an_automatic_wording_judge(tmp_path: Path) -> None:
    sheet, manifest = bundle(tmp_path)
    rate(sheet, [("yes", "yes")])
    report = summarize_ratings(sheet.read_bytes(), manifest.read_bytes())
    assert report["scoring_version"] == "learning-human-v1"
    assert report["totals"]["learned"] == {"yes": 1, "partly": 0, "no": 0}
    assert report["totals"]["answer_ok"]["yes"] == report["totals"]["successful_cases"] == 1
    assert "wrong_facts" not in report["totals"]
    public = json.dumps(report) + human_markdown(report)
    assert "PRIVATE" not in public and "private-001" not in public and "Use form A" not in public


def test_partly_is_separate_and_failed_spend_and_every_case_are_retained(tmp_path: Path) -> None:
    cases, trials = zip(*(example(index) for index in range(1, 4)), strict=True)
    trials = (*trials[:2], Trial(error="capture", cost_usd=Decimal("0.03")))
    sheet, manifest = tmp_path / "review.csv", tmp_path / "review.run.json"
    write_review(cases, trials, TODAY, sheet=sheet, manifest=manifest, metadata={"dataset_kind": "synthetic"})
    rate(sheet, [("yes", "yes"), ("partly", "no"), ("no", "partly")])
    report = summarize_ratings(sheet.read_bytes(), manifest.read_bytes())
    totals = report["totals"]
    assert totals["cases"] == 3 and totals["errors"] == 1
    assert totals["learned"] == totals["answer_ok"] == {"yes": 1, "partly": 1, "no": 1}
    assert totals["successful_cases"] == 1 and totals["cost_per_successful_case_usd"] == "0.05"
    assert "| learned | 1 | 1 | 1 | 3 |" in human_markdown(report)


@pytest.mark.parametrize("bad", ["", "good", "1", "=1+1", "PRIVATE INVALID LABEL"])
def test_incomplete_or_invalid_labels_are_rejected_without_echoing_private_values(tmp_path: Path, bad: str) -> None:
    sheet, manifest = bundle(tmp_path)
    rate(sheet, [("yes", bad)])
    with pytest.raises(ValueError) as error:
        summarize_ratings(sheet.read_bytes(), manifest.read_bytes())
    assert "PRIVATE INVALID LABEL" not in str(error.value)


@pytest.mark.parametrize("change", ["missing", "duplicate", "evidence", "header", "other-run"])
def test_reviews_cannot_silently_drop_duplicate_edit_or_mix_original_rows(tmp_path: Path, change: str) -> None:
    sheet, manifest = bundle(tmp_path, 2)
    rate(sheet, [("yes", "yes"), ("no", "partly")])
    rows = read(sheet)
    if change == "missing":
        rows.pop()
    elif change == "duplicate":
        rows.append(rows[1])
    elif change == "evidence":
        rows[1][2] = "PRIVATE CHANGED FACT"
    elif change == "header":
        rows[0][5] = "score"
    else:
        rows[1][0] = "PRIVATE OTHER RUN ID"
    save(sheet, rows)
    with pytest.raises(ValueError) as error:
        summarize_ratings(sheet.read_bytes(), manifest.read_bytes())
    assert "PRIVATE" not in str(error.value)


def test_rows_can_be_sorted_and_rating_case_or_whitespace_normalized(tmp_path: Path) -> None:
    sheet, manifest = bundle(tmp_path, 2)
    rate(sheet, [(" YES ", "Partly"), ("no", "yes")])
    rows = read(sheet)
    save(sheet, [rows[0], rows[2], rows[1], []])
    report = summarize_ratings(sheet.read_bytes(), manifest.read_bytes())
    assert [row["case"] for row in report["cases"]] == ["case-0001", "case-0002"]
    assert report["cases"][0]["learned"] == "yes"


def test_formula_like_private_text_is_exported_as_literal_spreadsheet_text(tmp_path: Path) -> None:
    case = Case(
        "case-0001",
        "Synthetic source",
        "@Synthetic question?",
        (("-Synthetic expected fact",),),
        club_id=CLUB,
        case_id="+001",
    )
    fact = verified(item(statement="=1+1"))
    trial = Trial(
        approved=(fact,),
        before=Answer(known=False, text="Unknown", basis="none", ask={"who": "Synthetic reviewer"}),
        after=Answer(known=True, text="=1+1", basis="verified", citations=[fact.item_id]),
    )
    sheet, manifest = tmp_path / "review.csv", tmp_path / "review.run.json"
    write_review([case], [trial], TODAY, sheet=sheet, manifest=manifest, metadata={})
    assert all(value.startswith("'") for value in read(sheet)[1][:5])
    rate(sheet, [("no", "no")])
    report = summarize_ratings(sheet.read_bytes(), manifest.read_bytes())
    assert report["totals"]["learned"]["no"] == 1 and not report["totals"]["cost_complete"]


def test_existing_review_ratings_or_companion_are_never_overwritten(tmp_path: Path) -> None:
    sheet, manifest = bundle(tmp_path)
    rate(sheet, [("yes", "partly")])
    before = sheet.read_bytes(), manifest.read_bytes()
    case, trial = example()
    with pytest.raises(ValueError, match="never overwritten"):
        write_review([case], [trial], TODAY, sheet=sheet, manifest=manifest, metadata={})
    assert before == (sheet.read_bytes(), manifest.read_bytes())


def test_unapproved_facts_are_not_presented_as_learned_and_missing_cost_is_not_zero(tmp_path: Path) -> None:
    case, _ = example()
    trial = Trial(proposed=(item(),), error="approval")
    sheet, manifest = tmp_path / "review.csv", tmp_path / "review.run.json"
    write_review([case], [trial], TODAY, sheet=sheet, manifest=manifest, metadata={})
    assert read(sheet)[1][2] == read(sheet)[1][4] == ""
    rate(sheet, [("no", "no")])
    report = summarize_ratings(sheet.read_bytes(), manifest.read_bytes())
    assert report["totals"]["errors"] == 1 and report["totals"]["cost_usd"] is None
    assert report["totals"]["cases"] == 1
