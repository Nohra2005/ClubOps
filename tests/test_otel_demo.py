import json

import httpx
import pytest

from clubops.reports.otel import ENDPOINT_ENV
from clubops.reports.otel_demo import DEMO_LABELS, main, synthetic_run
from clubops.reports.otel_payload import build_batch


def test_synthetic_demo_has_two_steps_and_two_replayed_calls() -> None:
    batch = build_batch(synthetic_run(), DEMO_LABELS)
    spans = json.loads(batch.body)["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert batch.span_count == 5
    assert [s["name"] for s in spans] == ["agent.run", "agent.step", "agent.step", "model.call", "model.call"]
    assert spans[3]["parentSpanId"] == spans[1]["spanId"]
    assert spans[4]["parentSpanId"] == spans[2]["spanId"]
    assert all(c.trace.replayed and c.trace.tokens_in == 0 for c in synthetic_run().calls)


def test_cli_disabled_by_default(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv(ENDPOINT_ENV, raising=False)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Disabled demo connected")

    monkeypatch.setattr(httpx, "Client", forbidden)
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "disabled"


def test_cli_reports_configuration_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--endpoint", "https://secret@invalid.example"]) == 1
    output = capsys.readouterr().out
    assert json.loads(output)["outcome"] == "invalid_endpoint"
    assert "secret" not in output
