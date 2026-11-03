"""C-27: private human-review sheets and explicit exact-word smoke diagnostics."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from clubops.contracts.common import ClubId, SourceKind
from clubops.contracts.knowhow import Answer, KnowHowItem, Scope


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
    case_id: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        TypeAdapter(ClubId).validate_python(self.club_id)
        if not re.fullmatch(r"case-\d{4,}", self.ref):
            raise ValueError("Case references must be opaque row numbers.")
        if len(self.case_id) > 200 or "\n" in self.case_id or "\r" in self.case_id:
            raise ValueError("Invalid private case id.")
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
    expected_format: Literal["json", "text"] = "json"
    id: str = "id"

    def __post_init__(self) -> None:
        required = (self.source, self.question, self.expected)
        if len(set(required)) != 3 or any(not name.strip() for name in required):
            raise ValueError("Source, question and expected-fact columns must be distinct and nonempty.")
        if self.expected_format not in ("json", "text"):
            raise ValueError("Unknown expected-fact format.")


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
        return parse_cases(path.read_text(encoding="utf-8-sig"), columns)
    except UnicodeError:
        raise ValueError("Invalid learning CSV encoding; private values omitted.") from None


def parse_cases(content: str, columns: Columns = DEFAULT_COLUMNS) -> list[Case]:
    """Parse a single frozen input snapshot so the report hash matches the actual evaluated rows."""
    try:
        with io.StringIO(content, newline="") as source:
            reader = csv.DictReader(source, strict=True)
            names = reader.fieldnames or []
            if len(set(names)) != len(names) or not {columns.source, columns.question, columns.expected} <= set(names):
                raise ValueError("Missing required or duplicate CSV columns.")
            cases: list[Case] = []
            ids: set[str] = set()
            for index, row in enumerate(reader, 1):
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("Uneven row.")
                    case = Case(
                        ref=f"case-{index:04d}",
                        source=row[columns.source],
                        question=row[columns.question],
                        expected=(
                            _labels(row[columns.expected])
                            if columns.expected_format == "json"
                            else ((row[columns.expected],),)
                            if row[columns.expected].strip()
                            else ()
                        ),
                        kind=SourceKind(row.get(columns.kind) or "user_input"),
                        club_id=row.get(columns.club) or "eval-club",
                        case_id=(row.get(columns.id) or "").strip(),
                    )
                    private_id = case.case_id or case.ref
                    if private_id in ids:
                        raise ValueError("Duplicate case id.")
                    ids.add(private_id)
                    cases.append(case)
                except (ValueError, TypeError, ValidationError):
                    raise ValueError(f"Invalid learning case at CSV row {index + 1}; private values omitted.") from None
            if not cases:
                raise ValueError("The learning dataset has no cases.")
            return cases
    except (csv.Error, UnicodeError):
        raise ValueError("Invalid learning CSV encoding or quoting; private values omitted.") from None


Phase = Literal["baseline", "capture", "approval", "answer", "runtime"]


@dataclass(frozen=True)
class Trial:
    proposed: tuple[KnowHowItem, ...] = field(default=(), repr=False)
    approved: tuple[KnowHowItem, ...] = field(default=(), repr=False)
    before: Answer | None = field(default=None, repr=False)
    after: Answer | None = field(default=None, repr=False)
    cost_usd: Decimal | None = None
    budget_steps: int = 0
    error: Phase | None = None

    def __post_init__(self) -> None:
        if self.cost_usd is not None and (not self.cost_usd.is_finite() or self.cost_usd < 0):
            raise ValueError("Invalid recorded cost.")
        if self.budget_steps < 0 or self.error not in (None, "baseline", "capture", "approval", "answer", "runtime"):
            raise ValueError("Invalid trial metadata.")


def score_case(case: Case, trial: Trial, on: date) -> dict[str, Any]:
    labels = {normalized(alias): index for index, group in enumerate(case.expected) for alias in group}

    def label(item: KnowHowItem) -> int | None:
        if item.scope is not Scope.CLUB or item.club_id != case.club_id:
            return None
        return labels.get(normalized(item.statement))

    visible = {item.item_id: item for item in trial.approved if item.is_current(on) and item.club_id == case.club_id}
    learned = {index for item in visible.values() if (index := label(item)) is not None}
    correct_ids = {item.item_id for item in visible.values() if label(item) is not None}
    unique = {(item.club_id, item.scope, normalized(item.statement)): item for item in trial.proposed}
    wrong = sum(label(item) is None for item in unique.values())
    duplicates = len(trial.proposed) - len(unique)
    error = trial.error or ("baseline" if trial.before is None else "answer" if trial.after is None else None)
    baseline_known = bool(trial.before and trial.before.known)
    supported = bool(
        trial.after
        and trial.after.known
        and trial.after.basis in ("verified", "single_source")
        and trial.after.citations
        and set(trial.after.citations) <= visible.keys()
        and correct_ids.intersection(trial.after.citations)
    )
    reused = supported and not baseline_known and error is None
    missed = len(case.expected) - len(learned)
    successful = (
        error is None
        and not baseline_known
        and not (wrong or missed or duplicates)
        and (reused if case.expected else bool(trial.after and not trial.after.known))
    )
    return {
        "case": case.ref,
        "expected_facts": len(case.expected),
        "facts_learned": len(learned),
        "wrong_facts": wrong,
        "missed_facts": missed,
        "duplicate_facts": duplicates,
        "answer_reused_new_fact": reused,
        "baseline_already_known": baseline_known,
        "unsupported_answer": bool(trial.after and trial.after.known and not supported),
        "successful": successful,
        "error": error,
        "budget_steps": trial.budget_steps,
        "cost_usd": str(trial.cost_usd) if trial.cost_usd is not None else None,
    }


def collect_trials(cases: Sequence[Case], system: Callable[[Case], Trial]) -> list[Trial]:
    """Run each case once, retaining operational failures for either review workflow."""
    trials: list[Trial] = []
    for case in cases:
        try:
            trial = system(case)
        except Exception:
            trial = Trial(error="runtime")  # no private exception messages; cost is unknown, not zero
        trials.append(trial)
    return trials


def evaluate(cases: Sequence[Case], system: Callable[[Case], Trial], on: date) -> dict[str, Any]:
    """Exact-word smoke diagnostic only; semantic quality comes from completed human ratings."""
    rows = [score_case(case, trial, on) for case, trial in zip(cases, collect_trials(cases, system), strict=True)]
    cost_complete = all(row["cost_usd"] is not None for row in rows)
    recorded_cost = sum((Decimal(row["cost_usd"]) for row in rows if row["cost_usd"] is not None), Decimal(0))
    success = sum(row["successful"] for row in rows)
    totals = {
        key: sum(row[key] for row in rows)
        for key in (
            "expected_facts",
            "facts_learned",
            "wrong_facts",
            "missed_facts",
            "duplicate_facts",
            "answer_reused_new_fact",
            "baseline_already_known",
            "unsupported_answer",
            "budget_steps",
        )
    }
    return {
        "scoring_version": "learning-exact-v1",
        "as_of": on.isoformat(),
        "totals": {
            "cases": len(rows),
            **totals,
            "successful_cases": success,
            "errors": sum(row["error"] is not None for row in rows),
            "cost_complete": cost_complete,
            "known_cost_usd": str(recorded_cost),
            "cost_usd": str(recorded_cost) if cost_complete else None,
            "cost_per_successful_case_usd": str(recorded_cost / success) if cost_complete and success else None,
        },
        "cases": rows,
        "limits": (
            "Exact normalized statements and pre-labelled aliases, not semantic accuracy. "
            "Answer reuse means a newly approved expected fact was cited, not that every answer claim was correct. "
            "Sandbox approvals are evaluator actions, not real-user acceptance."
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "# Learning evaluation",
        "",
        report["limits"],
        "",
        "| Case | Expected | Learned | Wrong | Missed | Duplicates | New fact cited | Error | Cost USD |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for row in report["cases"]:
        lines.append(
            f"| {row['case']} | {row['expected_facts']} | {row['facts_learned']} | {row['wrong_facts']} "
            f"| {row['missed_facts']} | {row['duplicate_facts']} | {int(row['answer_reused_new_fact'])} "
            f"| {row['error'] or '-'} | {row['cost_usd'] if row['cost_usd'] is not None else 'unavailable'} |"
        )
    lines.extend(
        [
            "",
            f"Cases: {totals['cases']}; errors: {totals['errors']}; successful: {totals['successful_cases']}.",
            f"Model cost USD: {totals['cost_usd'] if totals['cost_complete'] else 'unavailable'}.",
            "",
        ]
    )
    return "\n".join(lines)


REVIEW_COLUMNS = (
    "id",
    "fact I expected",
    "fact ClubOps learned",
    "question",
    "ClubOps's answer",
    "learned",
    "answer_ok",
)
REVIEW_FORMAT = "clubops-learning-review-v1"
RATINGS = ("yes", "partly", "no")
RUN_FIELDS = (
    "dataset_sha256",
    "dataset_kind",
    "mode",
    "model",
    "price_in_per_mtok",
    "price_out_per_mtok",
    "budget_usd_per_case",
    "max_steps_per_case",
    "sandbox_approval",
    "cost_accounting",
)


def _dangerous_cell(value: str) -> bool:
    return value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))


def _spreadsheet_text(value: str) -> str:
    if len(value) > 32767:
        raise ValueError("A review cell exceeds the spreadsheet text limit; nothing was truncated.")
    return "'" + value if _dangerous_cell(value) else value


def _review_fingerprint(values: Sequence[str]) -> str:
    canonical = []
    for value in values:
        text = value.replace("\r\n", "\n").replace("\r", "\n")
        if text.startswith("'") and _dangerous_cell(text[1:]):
            text = text[1:]  # accept a text-import round trip with or without our CSV safety prefix
        canonical.append(text)
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False).encode()).hexdigest()


def write_review(
    cases: Sequence[Case],
    trials: Sequence[Trial],
    on: date,
    *,
    sheet: Path,
    manifest: Path,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Export actual saved statements/answers and two blank human-rating columns.

    The CSV deliberately contains private text. Its companion retains only hashes,
    operational metadata and budget costs, never a second copy of the review text.
    Neither existing file is overwritten, especially a sheet with completed ratings.
    """
    if not cases or len(cases) != len(trials):
        raise ValueError("Review cases and trials must align.")
    if sheet.suffix.lower() != ".csv" or manifest.suffix.lower() != ".json":
        raise ValueError("Use a .csv review sheet and .json companion.")
    if sheet.resolve() == manifest.resolve() or sheet.exists() or manifest.exists():
        raise ValueError("Review outputs must be new, distinct files; existing ratings are never overwritten.")
    rows: list[list[str]] = []
    records: list[dict[str, Any]] = []
    for case, trial in zip(cases, trials, strict=True):
        learned = [
            item.statement
            for item in trial.approved
            if item.scope is Scope.CLUB and item.club_id == case.club_id and item.is_current(on)
        ]
        fixed = [
            _spreadsheet_text(value)
            for value in (
                case.case_id or case.ref,
                "\n".join(group[0] for group in case.expected),
                "\n".join(learned),
                case.question,
                trial.after.text if trial.after else "",
            )
        ]
        rows.append([*fixed, "", ""])
        error = trial.error or ("baseline" if trial.before is None else "answer" if trial.after is None else None)
        records.append(
            {
                "case": case.ref,
                "fixed_sha256": _review_fingerprint(fixed),
                "error": error,
                "baseline_already_known": bool(trial.before and trial.before.known),
                "cost_usd": str(trial.cost_usd) if trial.cost_usd is not None else None,
                "budget_steps": trial.budget_steps,
            }
        )
    run = {
        "format": REVIEW_FORMAT,
        "run_id": uuid4().hex,
        "as_of": on.isoformat(),
        **{key: metadata[key] for key in RUN_FIELDS if key in metadata},
        "cases": records,
    }
    content = json.dumps(run, indent=2) + "\n"
    sheet.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with sheet.open("x", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(REVIEW_COLUMNS)
        writer.writerows(rows)
    with manifest.open("x", encoding="utf-8") as output:
        output.write(content)
    return run
