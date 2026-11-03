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
from tests.test_learning_review import rate, read

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
        "smoke",
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
        eval_learning.main(["smoke", "--cases", str(path), "--as-of", "2026-10-29", "--out", str(path)])
    assert error.value.code == 2 and path.read_bytes() == before


@pytest.mark.usefixtures("environment")
def test_checked_in_synthetic_example_replays_without_an_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("CLUBOPS_API_KEY", "")

    def no_network(*_: object, **__: object) -> None:
        raise AssertionError("Checked-in replay attempted network access.")

    monkeypatch.setattr(httpx.Client, "send", no_network)
    code = eval_learning.main(
        [
            "smoke",
            "--cases",
            str(root / "tests/fixtures/learning.synthetic.csv"),
            "--as-of",
            "2026-10-29",
            "--dataset-kind",
            "synthetic",
            "--recordings",
            str(root / "tests/fixtures/learning-recordings"),
            "--json-out",
            str(tmp_path / "result.json"),
        ]
    )
    result = json.loads((tmp_path / "result.json").read_text())
    assert code == 0 and result["mode"] == "replay" and result["model"] == "fake-model"
    assert (result["totals"]["cases"], result["totals"]["facts_learned"], result["totals"]["errors"]) == (2, 1, 0)
    assert result["totals"]["cost_usd"] == "0"


def review_arguments(path: Path, tmp_path: Path) -> list[str]:
    return [
        "export",
        "--cases",
        str(path),
        "--as-of",
        "2026-10-29",
        "--dataset-kind",
        "synthetic",
        "--recordings",
        str(tmp_path / "recordings"),
        "--sheet",
        str(tmp_path / "review.csv"),
    ]


@pytest.mark.usefixtures("environment")
def test_export_then_offline_score_accepts_a_human_approved_paraphrase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = dataset(tmp_path / "cases.csv", [STATEMENT], source=STATEMENT, id="synthetic-row-1")
    frozen = path.read_bytes()
    paraphrase = "Use form A to book the synthetic studio."
    extraction = extracted()
    extraction["facts"][0]["statement"] = paraphrase
    response = {**answer(), "text": "Submit form A to reserve it."}
    provider = Provider(extraction, response)
    use_provider(monkeypatch, provider)
    assert eval_learning.main([*review_arguments(path, tmp_path), "--mode", "record"]) == 0
    assert STATEMENT not in capsys.readouterr().out and path.read_bytes() == frozen
    sheet = tmp_path / "review.csv"
    rows = read(sheet)
    assert rows[1] == [
        "synthetic-row-1",
        STATEMENT,
        paraphrase,
        "How do we reserve the synthetic studio?",
        "Submit form A to reserve it.",
        "",
        "",
    ]
    assert len(provider.prompts) == 2
    rate(sheet, [("yes", "yes")])  # Synthetic reviewer labels; not measured human-study results.

    def no_model(*_: object, **__: object) -> None:
        raise AssertionError("Scoring ratings must not configure or call a model.")

    monkeypatch.setattr(eval_learning, "TrackedClient", no_model)
    monkeypatch.setattr(eval_learning, "load_settings", no_model)
    assert (
        eval_learning.main(
            [
                "score",
                "--sheet",
                str(sheet),
                "--out",
                str(tmp_path / "graded.md"),
                "--json-out",
                str(tmp_path / "graded.json"),
            ]
        )
        == 0
    )
    report = json.loads((tmp_path / "graded.json").read_text())
    assert report["scoring_version"] == "learning-human-v1"
    assert report["totals"]["learned"]["yes"] == report["totals"]["answer_ok"]["yes"] == 1
    assert report["totals"]["successful_cases"] == 1 and report["totals"]["cost_usd"] == "0.0014"
    assert paraphrase not in (tmp_path / "graded.md").read_text()
    assert len(provider.prompts) == 2


@pytest.mark.usefixtures("environment")
def test_export_defaults_to_real_replay_without_key_network_or_automatic_ratings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("CLUBOPS_API_KEY", "")

    def no_network(*_: object, **__: object) -> None:
        raise AssertionError("Replay attempted a provider call.")

    monkeypatch.setattr(httpx.Client, "send", no_network)
    sheet = tmp_path / "review.csv"
    assert (
        eval_learning.main(
            [
                "export",
                "--cases",
                str(root / "tests/fixtures/learning.synthetic.csv"),
                "--as-of",
                "2026-10-29",
                "--dataset-kind",
                "synthetic",
                "--recordings",
                str(root / "tests/fixtures/learning-recordings"),
                "--sheet",
                str(sheet),
            ]
        )
        == 0
    )
    rows = read(sheet)
    assert len(rows) == 3 and all(row[5:] == ["", ""] for row in rows[1:])
    companion = json.loads(sheet.with_suffix(".run.json").read_text())
    assert companion["mode"] == "replay" and all(row["cost_usd"] == "0" for row in companion["cases"])
    with pytest.raises(SystemExit) as error:
        eval_learning.main(["score", "--sheet", str(sheet), "--out", str(tmp_path / "incomplete.md")])
    assert error.value.code == 2 and not (tmp_path / "incomplete.md").exists()


@pytest.mark.usefixtures("environment")
def test_exported_operational_failure_remains_in_the_human_results(tmp_path: Path) -> None:
    path = dataset(tmp_path / "cases.csv", [STATEMENT], source=STATEMENT)
    assert eval_learning.main(review_arguments(path, tmp_path)) == 2  # deliberately missing replay cassette
    sheet = tmp_path / "review.csv"
    assert read(sheet)[1][2] == read(sheet)[1][4] == ""
    rate(sheet, [("no", "no")])
    assert (
        eval_learning.main(
            [
                "score",
                "--sheet",
                str(sheet),
                "--json-out",
                str(tmp_path / "failed.json"),
            ]
        )
        == 2
    )
    report = json.loads((tmp_path / "failed.json").read_text())
    assert report["totals"]["cases"] == report["totals"]["errors"] == 1
    assert report["totals"]["learned"]["no"] == report["totals"]["answer_ok"]["no"] == 1
    assert report["cases"][0]["error"] == "capture"


def test_export_protects_frozen_input_existing_ratings_and_private_output_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = dataset(tmp_path / "cases.csv", [STATEMENT])
    frozen = path.read_bytes()

    def no_model(*_: object, **__: object) -> None:
        raise AssertionError("Invalid destinations must be refused before model setup.")

    monkeypatch.setattr(eval_learning, "TrackedClient", no_model)
    args = review_arguments(path, tmp_path)
    with pytest.raises(SystemExit):
        eval_learning.main([*args, "--sheet", str(path)])
    sheet = tmp_path / "review.csv"
    sheet.write_text("KEEP EXISTING HUMAN RATINGS", encoding="utf-8")
    with pytest.raises(SystemExit):
        eval_learning.main(args)
    assert sheet.read_text() == "KEEP EXISTING HUMAN RATINGS" and path.read_bytes() == frozen
    private = tmp_path / "untracked-private.csv"
    monkeypatch.setattr(eval_learning, "ROOT", tmp_path)  # explicit repo boundary, independent of OS temp location
    with pytest.raises(SystemExit):
        eval_learning.main([*args, "--sheet", str(private), "--dataset-kind", "private"])
    assert not private.exists()


def test_score_cannot_overwrite_its_sheet_or_companion(tmp_path: Path) -> None:
    sheet, manifest = tmp_path / "review.csv", tmp_path / "review.run.json"
    sheet.write_text("UNTOUCHED SHEET", encoding="utf-8")
    manifest.write_text("UNTOUCHED COMPANION", encoding="utf-8")
    with pytest.raises(SystemExit):
        eval_learning.main(["score", "--sheet", str(sheet), "--json-out", str(manifest)])
    assert manifest.read_text() == "UNTOUCHED COMPANION"
