from dataclasses import replace
from typing import Any

import httpx
import pytest

from clubops.reports.otel import ENDPOINT_ENV, export_run
from tests.otel_fixtures import observation
from tests.test_otel_payload import LABELS

ENDPOINT = "http://127.0.0.1:4318/v1/traces"


def test_disabled_without_endpoint_never_builds_or_connects(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Disabled telemetry touched data or network")

    monkeypatch.delenv(ENDPOINT_ENV, raising=False)
    monkeypatch.setattr("clubops.reports.otel.build_batch", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    assert export_run(observation()).outcome == "disabled"
    monkeypatch.setenv(ENDPOINT_ENV, ENDPOINT)
    assert export_run(observation(), endpoint="").outcome == "disabled"


@pytest.mark.parametrize(
    "endpoint",
    [
        "ftp://localhost/v1/traces",
        "http://remote.invalid/v1/traces",
        "https://secret@collector.invalid",
        "https://collector.invalid/?token=secret",
        "https://collector.invalid/#secret",
        "https://",
        "http://localhost:99999",
        "http://localhost:0",
        "https://collector.invalid/a\nsecret",
        "https://\ud800.invalid/v1/traces",
    ],
)
def test_invalid_endpoints_never_connect(endpoint: str) -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid endpoint connected")

    result = export_run(observation(), endpoint=endpoint, _transport=httpx.MockTransport(forbidden))
    assert result.outcome == "invalid_endpoint"
    assert "secret" not in repr(result)


def test_explicit_environment_export_is_json_and_private(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = []

    def collector(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        assert request.method == "POST" and str(request.url) == ENDPOINT
        assert request.headers["content-type"] == "application/json"
        for private in (b"Synthetic private description", b"running-club", b"run-synthetic", b"trace-synthetic"):
            assert private not in request.content
        return httpx.Response(200, json={})

    monkeypatch.setenv(ENDPOINT_ENV, ENDPOINT)
    result = export_run(observation(), labels=LABELS, _transport=httpx.MockTransport(collector))
    assert result.outcome == "accepted" and result.span_count == 3 and len(captured) == 1
    assert result.trace_id and len(result.trace_id) == 32


@pytest.mark.parametrize(
    ("reply", "outcome", "rejected"),
    [
        ({"partialSuccess": {"rejectedSpans": "1", "errorMessage": "private canary"}}, "partial", 1),
        ({"partialSuccess": {"rejectedSpans": 0, "errorMessage": "private canary"}}, "warning", 0),
        ({"partialSuccess": {}}, "accepted", 0),
        ({"partialSuccess": {"rejectedSpans": "0", "errorMessage": ""}}, "accepted", 0),
        ({"partialSuccess": {"errorMessage": 42}}, "invalid_response", 0),
        ({"partialSuccess": {"rejectedSpans": True}}, "invalid_response", 0),
        ({"partialSuccess": {"rejectedSpans": "99"}}, "invalid_response", 0),
        ({"partialSuccess": {"rejectedSpans": "-1"}}, "invalid_response", 0),
        ({"partialSuccess": None}, "invalid_response", 0),
        ([], "invalid_response", 0),
    ],
)
def test_partial_and_malformed_successes_are_not_silent(reply: Any, outcome: str, rejected: int) -> None:
    calls = []

    def collector(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=reply)

    result = export_run(observation(), endpoint=ENDPOINT, _transport=httpx.MockTransport(collector))
    assert result.outcome == outcome and result.rejected_spans == rejected
    assert "private canary" not in repr(result)
    assert len(calls) == 1 and not result.retryable


@pytest.mark.parametrize(("status", "retryable"), [(302, False), (400, False), (429, True), (503, True)])
def test_http_failures_no_redirect_or_automatic_retry(status: int, retryable: bool) -> None:
    calls = []

    def collector(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status, text="private canary", headers={"Location": "https://other.invalid"})

    result = export_run(observation(), endpoint=ENDPOINT, _transport=httpx.MockTransport(collector))
    assert result.outcome == "http_error" and result.retryable == retryable and len(calls) == 1
    assert "private canary" not in repr(result)


@pytest.mark.parametrize("kind", ["timeout", "html", "oversized", "bad-json", "compressed"])
def test_transport_and_response_limits(kind: str) -> None:
    def collector(request: httpx.Request) -> httpx.Response:
        if kind == "timeout":
            raise httpx.ReadTimeout("private canary", request=request)
        if kind == "html":
            return httpx.Response(200, text="private canary", headers={"Content-Type": "text/html"})
        if kind == "compressed":
            # Never attempt decoding, even when an identity-only request was ignored.
            return httpx.Response(
                200,
                stream=httpx.ByteStream(b"not valid gzip"),
                headers={
                    "Content-Type": "application/json",
                    "Content-Encoding": "gzip",
                },
            )
        content = b"x" * 70_000 if kind == "oversized" else b"not JSON: private canary"
        return httpx.Response(200, content=content, headers={"Content-Type": "application/json"})

    result = export_run(observation(), endpoint=ENDPOINT, _transport=httpx.MockTransport(collector))
    assert result.outcome == ("transport_error" if kind == "timeout" else "invalid_response")
    assert "private canary" not in repr(result)


def test_invalid_observation_never_connects() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid observation connected")

    value = replace(observation(), steps=())
    assert (
        export_run(value, endpoint=ENDPOINT, _transport=httpx.MockTransport(forbidden)).outcome == "invalid_observation"
    )
