"""C-27 uses only synthetic annotations and the shared synthetic item factory."""

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from clubops.contracts.common import SourceKind
from clubops.contracts.knowhow import Answer
from clubops.evaluation.learning import Case, Columns, Trial, evaluate, load_cases, markdown, normalized, score_case
from tests.factories import CLUB, TODAY, item, source, verified


def dataset(path: Path, expected: object, **extra: str) -> Path:
    row = {
        "source": "Use the synthetic studio reservation form.",
        "question": "How do we reserve the synthetic studio?",
        "expected_facts": json.dumps(expected),
        **extra,
    }
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return path


def test_loader_accepts_bom_labels_aliases_and_optional_club_context(tmp_path: Path) -> None:
    [case] = load_cases(dataset(tmp_path / "cases.csv", [["Use form A.", "Submit form A."]], source_kind="email"))
    assert case.ref == "case-0001" and case.kind is SourceKind.EMAIL
    assert case.expected == (("Use form A.", "Submit form A."),)
    assert "synthetic studio" not in repr(case)
    assert normalized(" USE  Form A! ") == normalized("Use form A.")
    assert normalized("Do not use form A") != normalized("Use form A")


@pytest.mark.parametrize("labels", ["PRIVATE LABEL", [[123]], [[]], ["same fact", ["SAME FACT!"]]])
def test_invalid_labels_do_not_echo_private_values(tmp_path: Path, labels: object) -> None:
    with pytest.raises(ValueError, match="CSV row 2; private values omitted") as error:
        load_cases(dataset(tmp_path / "cases.csv", labels))
    assert "PRIVATE LABEL" not in str(error.value)


def test_empty_negative_case_and_explicit_column_mapping(tmp_path: Path) -> None:
    path = tmp_path / "different.csv"
    path.write_text('excerpt,follow_up,labels\n"Synthetic note",Question?,[]\n', encoding="utf-8")
    [case] = load_cases(path, Columns(source="excerpt", question="follow_up", expected="labels"))
    assert case.expected == ()
    with pytest.raises(ValueError, match="columns"):
        load_cases(path)


def test_existing_plain_fact_column_can_be_mapped_without_rewriting_the_frozen_file(tmp_path: Path) -> None:
    path = tmp_path / "original.csv"
    path.write_text("excerpt,follow_up,fact\nSynthetic source,Question?,Use the example form.\n", encoding="utf-8")
    before = path.read_bytes()
    [loaded] = load_cases(
        path, Columns(source="excerpt", question="follow_up", expected="fact", expected_format="text")
    )
    assert loaded.expected == (("Use the example form.",),) and path.read_bytes() == before


def test_taught_and_expected_fact_can_share_a_frozen_column(tmp_path: Path) -> None:
    path = tmp_path / "original.csv"
    path.write_text(
        "l_id,fact,later_question\nsynthetic-001,Use the example form.,Which form do we use?\n", encoding="utf-8"
    )
    before = path.read_bytes()
    [loaded] = load_cases(
        path,
        Columns(source="fact", question="later_question", expected="fact", expected_format="text", id="l_id"),
    )
    assert loaded.source == loaded.expected[0][0] == "Use the example form."
    assert loaded.case_id == "synthetic-001" and path.read_bytes() == before


@pytest.mark.parametrize(
    "columns",
    [
        {"source": "question"},
        {"expected": "question"},
        {"source": ""},
        {"question": " "},
        {"expected": ""},
    ],
)
def test_question_stays_separate_and_required_column_names_stay_nonempty(columns: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="nonempty.*question.*separate"):
        Columns(**columns)


def test_private_case_ids_are_preserved_for_review_but_not_public_refs(tmp_path: Path) -> None:
    path = dataset(tmp_path / "cases.csv", ["Synthetic expected fact"], id="private-001")
    [loaded] = load_cases(path)
    assert loaded.case_id == "private-001" and loaded.ref == "case-0001"
    assert "private-001" not in repr(loaded)
    with path.open("a", encoding="utf-8", newline="") as output:
        output.write('Another synthetic source,Question?,"[]",private-001\n')
    with pytest.raises(ValueError, match="private values omitted"):
        load_cases(path)


def test_case_rejects_scope_escape_and_invalid_lengths() -> None:
    with pytest.raises(ValueError):
        Case("case-0001", "Synthetic note", "Question?", (), club_id="../private")
    with pytest.raises(ValueError, match="length"):
        Case("case-0001", "", "Question?", ())


STATEMENT = "Reserve the synthetic studio with form A."


def case(ref: str = "case-0001") -> Case:
    return Case(ref, "PRIVATE SOURCE", "A private test question?", ((STATEMENT,),), club_id=CLUB)


def unknown() -> Answer:
    return Answer(known=False, text="PRIVATE ANSWER", basis="none", ask={"who": "Synthetic reviewer"})


def trial(**updates: object) -> Trial:
    candidate = item(statement=STATEMENT, sources=[source(quote=STATEMENT)])
    values = {
        "proposed": (candidate,),
        "approved": (verified(candidate),),
        "before": unknown(),
        "after": Answer(known=True, text="PRIVATE ANSWER", basis="verified", citations=[candidate.item_id]),
        "cost_usd": Decimal("0.01"),
        "budget_steps": 2,
        **updates,
    }
    return Trial(**values)  # type: ignore[arg-type]


def test_counts_verified_exact_facts_and_new_citations_without_reporting_private_content() -> None:
    report = evaluate([case()], lambda _: trial(), TODAY)
    assert report["totals"]["facts_learned"] == 1
    assert report["totals"]["successful_cases"] == 1
    assert report["totals"]["answer_reused_new_fact"] == 1
    public = json.dumps(report) + markdown(report)
    for private in [STATEMENT, "PRIVATE SOURCE", "PRIVATE ANSWER", "private test question"]:
        assert private not in public


def test_negation_duplicates_foreign_and_unapproved_items_do_not_inflate_learning() -> None:
    wrong = item("kh-wrong", statement="Do not reserve the synthetic studio with form A.")
    foreign = item("kh-foreign", statement=STATEMENT, club_id="other-club")
    unapproved = item("kh-pending", statement=STATEMENT)
    result = score_case(
        case(), trial(proposed=(wrong, wrong, foreign), approved=(verified(foreign), unapproved)), TODAY
    )
    assert (result["facts_learned"], result["wrong_facts"], result["missed_facts"], result["duplicate_facts"]) == (
        0,
        2,
        1,
        1,
    )
    assert not result["answer_reused_new_fact"] and result["unsupported_answer"]


def test_preexisting_answers_expired_facts_and_wrong_citations_do_not_claim_reuse() -> None:
    correct = trial()
    assert not score_case(case(), trial(before=correct.after), TODAY)["successful"]
    expired = verified(item(statement=STATEMENT)).model_copy(update={"valid_to": date(2026, 1, 1)})
    assert score_case(case(), trial(approved=(expired,)), TODAY)["facts_learned"] == 0
    wrong = Answer(known=True, text="PRIVATE ANSWER", basis="verified", citations=["kh-not-in-this-case"])
    assert not score_case(case(), trial(after=wrong), TODAY)["answer_reused_new_fact"]


def test_failed_cases_stay_in_denominators_and_failed_spend_is_in_cost_per_success() -> None:
    def system(value: Case) -> Trial:
        return (
            trial()
            if value.ref == "case-0001"
            else trial(approved=(), after=None, error="capture", cost_usd=Decimal("0.02"))
        )

    report = evaluate([case(), case("case-0002")], system, TODAY)
    totals = report["totals"]
    assert (totals["cases"], totals["expected_facts"], totals["facts_learned"], totals["missed_facts"]) == (2, 2, 1, 1)
    assert totals["cost_per_successful_case_usd"] == "0.03" and totals["errors"] == 1


def test_unexpected_failure_has_unknown_cost_not_a_measured_zero() -> None:
    def broken(_: Case) -> Trial:
        raise RuntimeError("PRIVATE PROVIDER DIAGNOSTIC")

    report = evaluate([case()], broken, TODAY)
    assert report["totals"]["missed_facts"] == 1
    assert not report["totals"]["cost_complete"] and report["totals"]["cost_usd"] is None
    assert "PRIVATE PROVIDER DIAGNOSTIC" not in json.dumps(report)


def test_negative_case_can_succeed_only_without_a_fabricated_answer() -> None:
    negative = Case("case-0001", "Synthetic off-topic note", "Any new fact?", (), club_id=CLUB)
    result = score_case(negative, Trial(before=unknown(), after=unknown(), cost_usd=Decimal(0)), TODAY)
    assert result["successful"]
