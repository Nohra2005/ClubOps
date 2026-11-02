"""C-27 uses only synthetic annotations and the shared synthetic item factory."""

import csv
import json
from pathlib import Path

import pytest

from clubops.contracts.common import SourceKind
from clubops.evaluation.learning import Case, Columns, load_cases, normalized


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


def test_case_rejects_scope_escape_and_invalid_lengths() -> None:
    with pytest.raises(ValueError):
        Case("case-0001", "Synthetic note", "Question?", (), club_id="../private")
    with pytest.raises(ValueError, match="length"):
        Case("case-0001", "", "Question?", ())
