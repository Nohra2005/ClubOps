"""The planning evaluation (T-06): labels, baselines, the no-leakage rule and the scoring maths.
Synthetic events only; the real test events stay private (eval/FROZEN.md)."""

from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from clubops.agent.planner import Planner
from clubops.config import ModelMode, Settings
from clubops.evaluation.plans import (
    PLAIN_VERSION,
    Case,
    ClubOpsSystem,
    Prediction,
    checklist,
    codes_by_rule,
    describe,
    facts_before,
    load_cases,
    model_baseline,
    rulebook_text,
    score,
    table,
    truth_codes,
)
from clubops.knowhow.directory import Directory
from clubops.knowhow.store import KnowHowStore
from clubops.model.budget import Budget
from clubops.model.client import ModelClient
from tests.factories import rule, verified
from tests.test_planner_agent import Script, full_plan

ROW = {
    "id": "S01",
    "date": "2026-03-14",
    "event": "Sunrise fun run",
    "place": "Green Field",
    "people": "40",
    "outside_guests": "yes, friends",
    "sponsors_prizes": "",
    "money": "",
    "partners": "",
    "notes": "SECRET NOTE: needed GUEST approval",
    "approvals_real (you fill)": "PROP ADV GUEST HOST, no SPON",
}


def case(cid: str = "S01", on: str = "2026-03-14", truth: str = "PROP GUEST", text: str = "Run") -> Case:
    return Case(cid, date.fromisoformat(on), text, truth_codes(truth))


def write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


# ------------------------------------------------------------------ labels


def test_codes_written_as_no_x_and_unknown_words_are_not_counted() -> None:
    assert truth_codes("PROP ADV GUEST, no SPON, maybe LATER") == {"PROP", "ADV", "GUEST"}


def test_the_description_never_uses_the_notes_or_the_label() -> None:
    text = describe(ROW)
    assert "Green Field" in text and "friends" in text
    assert "SECRET" not in text and "approvals" not in text.lower()
    assert "Sponsors" not in text  # empty fields are left out


def test_unlabelled_and_dropped_events_are_skipped(tmp_path: Path) -> None:
    rows = [
        ROW,
        {**ROW, "id": "S02", "approvals_real (you fill)": ""},
        {**ROW, "id": "S03", "approvals_real (you fill)": "DROP: duplicate"},
    ]
    cases = load_cases(write_csv(tmp_path / "events.csv", rows))
    assert [c.case_id for c in cases] == ["S01"]
    assert cases[0].on == date(2026, 3, 14) and cases[0].truth == {"PROP", "ADV", "GUEST", "HOST"}


# ------------------------------------------------------------------ systems


def test_the_checklist_ticks_by_keywords_and_costs_nothing() -> None:
    pred = checklist(case(text="Charity run on Green Field with a sponsor and prizes"))
    assert {"PROP", "ADV", "IMPACT", "HOST", "SPON", "PRIZE", "FUND"} <= pred.codes
    assert pred.cost_usd == 0 and pred.calls == 0


def settings(tmp_path: Path) -> Settings:
    return Settings(  # type: ignore[call-arg]
        base_url="https://provider.test/v1",
        api_key=SecretStr("sk-test"),
        model="fake-model",
        price_in_per_mtok=Decimal("1"),
        price_out_per_mtok=Decimal("2"),
        budget_usd_per_packet=Decimal("0.05"),
        max_steps_per_plan=8,
        mode=ModelMode.LIVE,
        recordings_dir=tmp_path / "rec",
        trace_path=tmp_path / "trace.jsonl",
    )


def fake_model(tmp_path: Path, content: str, seen: list[dict[str, Any]], status: int = 200) -> ModelClient:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            status,
            json={
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 500, "completion_tokens": 50},
            },
        )

    return ModelClient(settings(tmp_path), transport=httpx.MockTransport(handle))


def test_the_model_baseline_keeps_only_known_codes_and_counts_its_cost(tmp_path: Path) -> None:
    seen: list[dict[str, Any]] = []
    client = fake_model(tmp_path, json.dumps({"codes": ["prop", "GUEST", "MADEUP"]}), seen)
    pred = model_baseline(client, "- [GUEST] Guests: need approval")(case(text="Run with outside guests"))
    assert pred.codes == {"PROP", "GUEST"} and pred.calls == 1 and pred.cost_usd > 0
    prompt = json.dumps(seen[0])
    assert "AUB rules" in prompt and "<event>" in prompt


def test_without_the_rulebook_no_rules_are_sent(tmp_path: Path) -> None:
    seen: list[dict[str, Any]] = []
    model_baseline(fake_model(tmp_path, json.dumps({"codes": []}), seen), None)(case())
    assert "AUB rules" not in json.dumps(seen[0])


def test_a_failed_model_call_scores_as_no_codes_and_an_error(tmp_path: Path) -> None:
    pred = model_baseline(fake_model(tmp_path, "not json at all", []), None)(case())
    assert pred.codes == frozenset() and pred.error is not None


def test_each_repeated_run_has_its_own_recordings(tmp_path: Path) -> None:
    calls: list[str] = []

    class Spy(ModelClient):
        def complete(self, request: Any, schema: Any, budget: Budget) -> Any:
            calls.append(request.prompt_version)
            raise RuntimeError("stop")

    client = Spy(settings(tmp_path))
    model_baseline(client, None)(case())
    model_baseline(client, None, run=2)(case())
    assert calls == [PLAIN_VERSION, f"{PLAIN_VERSION}#r2"]


def test_clubops_reads_the_codes_from_the_rules_it_applied(tmp_path: Path) -> None:
    guests = verified(rule()).model_copy(update={"tags": ["guests", "guest"]})

    def store_for(_: Case) -> KnowHowStore:
        store = KnowHowStore()
        store.backend.append(guests)
        return store

    def make(store: KnowHowStore, directory: Directory, _: object) -> Planner:
        return Planner(Script(*full_plan()), store, directory)

    system = ClubOpsSystem(
        make, store_for, lambda c: Directory(tmp_path / c.case_id, "eval-club"), codes_by_rule([guests])
    )
    pred = system(case(text="Fun run on Green Field on 25 Oct, open to friends from outside AUB"))
    assert pred.codes == {"GUEST"} and pred.error is None and pred.calls == 5
    assert rulebook_text([guests]).startswith("- [GUEST] Non-AUB guests need approval")


def test_a_clubops_crash_is_scored_as_an_error_not_a_crash(tmp_path: Path) -> None:
    class Broken:
        def start(self, *_: object) -> None:
            raise RuntimeError("provider down")

    system = ClubOpsSystem(
        lambda *_: Broken(),  # type: ignore[arg-type, return-value]
        lambda _: KnowHowStore(),
        lambda c: Directory(tmp_path / c.case_id, "eval-club"),
    )
    pred = system(case())
    assert pred.codes == frozenset() and pred.error == "RuntimeError"


# ------------------------------------------------------------------ no leakage


def test_only_facts_from_earlier_events_are_given_to_clubops(tmp_path: Path) -> None:
    cases = [case("S01", "2026-03-01"), case("S02", "2026-04-01"), case("S03", "2026-05-01")]
    facts = write_csv(
        tmp_path / "facts.csv",
        [
            {
                "fact_id": "F1",
                "statement": "Book Green Field three weeks ahead",
                "scope": "club",
                "learned_from_event": "S01",
            },
            {
                "fact_id": "F2",
                "statement": "Coffee sponsor needs a logo on the poster",
                "scope": "club",
                "learned_from_event": "S02",
            },
            {"fact_id": "F3", "statement": "OSA answers in about a week", "scope": "aub", "learned_from_event": ""},
            {
                "fact_id": "F4",
                "statement": "From an event we do not know",
                "scope": "club",
                "learned_from_event": "X99",
            },
        ],
    )
    got = {i.item_id for i in facts_before(facts, cases, date(2026, 4, 1), "eval-club")}
    assert got == {"kh-fact-f1", "kh-fact-f3"}  # S02 is the same day: not before; X99 unknown: left out
    assert all(i.scope.value == "club" for i in facts_before(facts, cases, date(2026, 6, 1), "eval-club"))


# ------------------------------------------------------------------ scoring


def test_scores_count_misses_false_alarms_and_unsure_flags() -> None:
    cases = [case("S01", truth="PROP GUEST HOST"), case("S02", truth="PROP")]
    answers = {
        "S01": Prediction(frozenset({"PROP", "FOOD"}), frozenset({"GUEST"}), Decimal("0.01"), 2),
        "S02": Prediction(frozenset({"PROP"}), error="at_limit"),
    }
    s = score(cases, lambda c: answers[c.case_id])
    assert (s.caught, s.missed, s.false_alarms, s.unsure_caught, s.errors, s.calls) == (2, 2, 1, 1, 1, 2)
    assert s.recall == 0.5 and s.precision == pytest.approx(2 / 3) and s.f1 == pytest.approx(4 / 7)
    assert s.rows[0]["missed"] == ["GUEST", "HOST"]
    out = table({"test": s}, 2)
    assert "| test | 0.50 | 0.67 | 0.57 | 2 | 1 | 1 | 2 | 0.0100 | 0.0050 | 1 |" in out
