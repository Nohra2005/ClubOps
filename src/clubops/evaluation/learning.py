"""C-27: labelled learning cases and deterministic scoring; never a model-based judge."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from clubops.contracts.common import ClubId, SourceKind


def normalized(text: str) -> str:
    """Exact wording modulo Unicode normalization, case, punctuation and whitespace."""
    return re.sub(r"[^\w]+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


@dataclass(frozen=True)
class Case:
    ref: str
    source: str = field(repr=False)
    question: str = field(repr=False)
    expected: tuple[tuple[str, ...], ...] = field(repr=False)
    kind: SourceKind = SourceKind.USER_INPUT
    club_id: str = "eval-club"

    def __post_init__(self) -> None:
        TypeAdapter(ClubId).validate_python(self.club_id)
        if not re.fullmatch(r"case-\d{4,}", self.ref):
            raise ValueError("Case references must be opaque row numbers.")
        if not self.source.strip() or len(self.source) > 20_000 or not 3 <= len(self.question.strip()) <= 500:
            raise ValueError("Invalid source or question length.")
        seen: set[str] = set()
        for aliases in self.expected:
            values = {normalized(alias) for alias in aliases}
            if not aliases or "" in values or any(len(alias) > 1500 for alias in aliases) or seen & values:
                raise ValueError("Expected facts need nonempty, unambiguous labelled wording.")
            seen.update(values)


@dataclass(frozen=True)
class Columns:
    source: str = "source"
    question: str = "question"
    expected: str = "expected_facts"
    kind: str = "source_kind"
    club: str = "club_id"


def _labels(raw: str) -> tuple[tuple[str, ...], ...]:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array.")
    groups: list[tuple[str, ...]] = []
    for value in data:
        aliases = [value] if isinstance(value, str) else value
        if not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
            raise ValueError("Expected labelled statements or alias groups.")
        groups.append(tuple(aliases))
    return tuple(groups)


DEFAULT_COLUMNS = Columns()


def load_cases(path: Path, columns: Columns = DEFAULT_COLUMNS) -> list[Case]:
    """Private CSV in; sanitized row-level validation errors out. No label/source values echoed."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            names = reader.fieldnames or []
            if len(set(names)) != len(names) or not {columns.source, columns.question, columns.expected} <= set(names):
                raise ValueError("Missing required or duplicate CSV columns.")
            cases: list[Case] = []
            for index, row in enumerate(reader, 1):
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("Uneven row.")
                    cases.append(
                        Case(
                            ref=f"case-{index:04d}",
                            source=row[columns.source],
                            question=row[columns.question],
                            expected=_labels(row[columns.expected]),
                            kind=SourceKind(row.get(columns.kind) or "user_input"),
                            club_id=row.get(columns.club) or "eval-club",
                        )
                    )
                except (ValueError, TypeError, ValidationError):
                    raise ValueError(f"Invalid learning case at CSV row {index + 1}; private values omitted.") from None
            if not cases:
                raise ValueError("The learning dataset has no cases.")
            return cases
    except (csv.Error, UnicodeError):
        raise ValueError("Invalid learning CSV encoding or quoting; private values omitted.") from None
