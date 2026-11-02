"""Real learner/store/chat composition: fake provider records once, then replay is forbidden any network."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from scripts import eval_learning

from clubops.config import Settings
from tests.factories import item, source
from tests.test_eval_learning import STATEMENT, dataset
from tests.test_learning import Provider

CLIENT = eval_learning.TrackedClient


def extracted() -> dict[str, Any]:
    fact = item(
        title="Synthetic studio reservation",
        statement=STATEMENT,
        sources=[source(quote=STATEMENT)],
        details={
            "kind": "procedure",
            "goal": "Reserve the synthetic studio",
            "steps": [{"order": 1, "action": STATEMENT}],
        },
    )
    return {
        "facts": [
            {
                "kind": "procedure",
                "title": fact.title,
                "statement": fact.statement,
                "quote": STATEMENT,
                "source": 0,
                "details": fact.details.model_dump(mode="json"),
            }
        ]
    }


def answer(number: int = 1) -> dict[str, object]:
    return {"known": True, "text": STATEMENT, "basis": "verified", "citations": [f"kh-learn-case-{number:04d}-1"]}


@pytest.fixture
def environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "CLUBOPS_MODEL_MODE": "live",  # the CLI must still default to replay, not inherit this
        "CLUBOPS_BASE_URL": "https://provider.test/v1",
        "CLUBOPS_API_KEY": "sk-synthetic-test",
        "CLUBOPS_MODEL": "fake-model",
        "CLUBOPS_PRICE_IN_PER_MTOK": "1",
        "CLUBOPS_PRICE_OUT_PER_MTOK": "2",
        "CLUBOPS_TRACE_PATH": str(tmp_path / "metadata.jsonl"),
    }.items():
        monkeypatch.setenv(key, value)


def arguments(path: Path, tmp_path: Path) -> list[str]:
    return [
        "--cases",
        str(path),
        "--as-of",
        "2026-10-29",
        "--dataset-kind",
        "synthetic",
        "--recordings",
        str(tmp_path / "recordings"),
        "--out",
        str(tmp_path / "report.md"),
        "--json-out",
        str(tmp_path / "report.json"),
    ]


def use_provider(monkeypatch: pytest.MonkeyPatch, provider: Provider) -> None:
    def client(settings: Settings) -> CLIENT:
        return CLIENT(settings, transport=provider.transport())

    monkeypatch.setattr(eval_learning, "TrackedClient", client)


@pytest.mark.usefixtures("environment")
def test_record_then_real_replay_keeps_fact_ids_stable_and_never_uses_the_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = dataset(tmp_path / "cases.csv", [STATEMENT], source=STATEMENT)
    provider = Provider(extracted(), answer())
    use_provider(monkeypatch, provider)
    args = arguments(path, tmp_path)
    assert eval_learning.main([*args, "--mode", "record"]) == 0
    recorded = json.loads((tmp_path / "report.json").read_text())
    assert recorded["totals"]["successful_cases"] == 1
    assert recorded["totals"]["cost_usd"] == "0.0014" and len(provider.prompts) == 2
    monkeypatch.setattr(eval_learning, "TrackedClient", CLIENT)

    def no_network(*_: object, **__: object) -> None:
        raise AssertionError("Replay attempted network access.")

    monkeypatch.setattr(httpx.Client, "send", no_network)
    assert eval_learning.main(args) == 0  # no --mode: overrides the ambient live configuration
    replayed = json.loads((tmp_path / "report.json").read_text())
    assert replayed["mode"] == "replay" and replayed["totals"]["successful_cases"] == 1
    assert replayed["totals"]["cost_usd"] == "0" and replayed["totals"]["budget_steps"] == 2
    assert replayed["dataset_sha256"] == recorded["dataset_sha256"]
    assert STATEMENT not in (tmp_path / "report.md").read_text()
    assert STATEMENT not in json.dumps(replayed)


@pytest.mark.usefixtures("environment")
def test_missing_replay_record_is_an_error_not_a_zero_quality_measurement(tmp_path: Path) -> None:
    path = dataset(tmp_path / "cases.csv", [STATEMENT], source=STATEMENT)
    assert eval_learning.main(arguments(path, tmp_path)) == 2
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["totals"]["errors"] == 1 and report["totals"]["missed_facts"] == 1
    assert report["cases"][0]["error"] == "capture"


@pytest.mark.usefixtures("environment")
def test_failed_extraction_spend_and_later_cases_are_retained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = dataset(tmp_path / "cases.csv", [STATEMENT], source=STATEMENT)
    with path.open(encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        rows = list(reader)
        names = reader.fieldnames
    assert names is not None
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows * 2)
    provider = Provider("PRIVATE MALFORMED MODEL RESPONSE", extracted(), answer(2))
    use_provider(monkeypatch, provider)
    assert eval_learning.main([*arguments(path, tmp_path), "--mode", "record"]) == 2
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["totals"]["cases"] == 2 and report["totals"]["successful_cases"] == 1
    assert report["totals"]["cost_usd"] == "0.0021"
    assert report["cases"][0]["error"] == "capture" and report["cases"][1]["error"] is None
    assert "PRIVATE MALFORMED MODEL RESPONSE" not in json.dumps(report)


@pytest.mark.usefixtures("environment")
def test_ground_truth_canary_never_enters_model_prompts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = dataset(tmp_path / "cases.csv", ["GROUND TRUTH ONLY MUST NEVER REACH THE MODEL"], source=STATEMENT)
    provider = Provider({"facts": []})
    use_provider(monkeypatch, provider)
    assert eval_learning.main([*arguments(path, tmp_path), "--mode", "record"]) == 0
    assert provider.prompts and all("GROUND TRUTH ONLY" not in prompt for prompt in provider.prompts)


def test_output_cannot_overwrite_frozen_input(tmp_path: Path) -> None:
    path = dataset(tmp_path / "cases.csv", [STATEMENT])
    before = path.read_bytes()
    with pytest.raises(SystemExit) as error:
        eval_learning.main(["--cases", str(path), "--as-of", "2026-10-29", "--out", str(path)])
    assert error.value.code == 2 and path.read_bytes() == before
