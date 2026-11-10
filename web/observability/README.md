# C-25: optional metadata-only traces

This is a closed-run OTLP/HTTP JSON exporter and a reproducible **synthetic**
Jaeger demonstration. It does not instrument the application automatically.
Tatiana still owns the real agent/model producer hooks; C-20's provider validation
and C-26's deployed monitoring are separate pending work. C-25 stays `doing`.

## Run the local demonstration

From the repository root, with the normal Python environment and Docker running:

```powershell
docker compose -p clubops-otel -f web/observability/compose.yaml up -d
.venv/Scripts/python.exe -m clubops.reports.otel_demo --endpoint http://127.0.0.1:4318/v1/traces
```

The CLI prints an `accepted` result and an opaque `trace_id`. Open
`http://127.0.0.1:16686/trace/<trace_id>` to see:

```text
agent.run
  agent.step (search-memory)
    model.call
  agent.step (apply-rules)
    model.call
```

These are fixture timings (two seconds, two 200 ms calls), zero tokens/cost,
`replayed=true` and model `synthetic-no-provider`. No model, real club document,
agent execution or performance measurement is involved. Repeating the command
creates a new trace with new random IDs. The viewer has no authentication and
binds only to loopback; use synthetic data. Its default memory storage disappears
when the collector stops. Stop only this demonstration with:

```powershell
docker compose -p clubops-otel -f web/observability/compose.yaml down
```

The image is pinned to Jaeger 2.23.0 and its registry digest in `compose.yaml`.
The [official Jaeger guide](https://www.jaegertracing.io/docs/2.23/getting-started/)
describes this local viewer and its transient storage. The exporter follows the
[OTLP/HTTP JSON specification](https://opentelemetry.io/docs/specs/otlp/): hexadecimal
IDs, integer enum values, decimal-string nanosecond timestamps and JSON requests
to the configured trace URL (normally `/v1/traces`). No SDK dependency was added.

## Exact producer boundary for Tatiana

Use only the public `AgentRun`, `TraceMeta`, `Status` and `ErrorCode` contracts.
The wrapper types in `clubops.reports.otel_input` are private to this optional
reporting feature; they do not extend or change contracts 0.2.3.

```python
from clubops.reports.otel import export_run
from clubops.reports.otel_input import ModelObservation, RunObservation, StepWindow
from clubops.reports.otel_payload import PublicLabels

# Populate these from actual producer context and aware UTC timestamps.
# Do not infer them from arrival order or the unrelated JSONL reporting files.
observation = RunObservation(
    run=completed_run,
    started_at=actual_run_start,
    ended_at=actual_run_end,
    steps=(StepWindow(n=1, started_at=actual_step_start, ended_at=actual_step_end),),
    calls=(ModelObservation(
        club_id=completed_run.club_id,
        run_id=completed_run.run_id,
        step_n=1,
        trace=actual_model_call_trace,
        status=call_status,
        error=call_error_code_or_none,
    ),),
)
# Exact reviewed technical values from server configuration; never form content.
labels = PublicLabels(
    tools=public_tool_names,
    capabilities=public_capability_names,
    capability_versions=public_capability_versions,
    prompt_versions=public_prompt_versions,
    models=public_model_identifiers,
)
result = export_run(observation, labels=labels)
```

The variables above are a wiring illustration, not an executable application
snippet. Include **every** run step and every observed model call, with each call
explicitly associated with its own step. `TraceMeta` must describe the actual
model call: do not relabel a whole capability's end-to-end latency as model time.
Steps with no model call are allowed. Cross-club/run calls, duplicate trace IDs,
missing/duplicate windows, naive/reversed/out-of-range times and calls outside
their step are rejected with a sanitized error. Windows must fit inside the run.

Only completed snapshots (`done`, `failed`, or an explicitly finalized `at_limit`)
are accepted. Do not export an intermediate limit stop if it will be continued,
or `running`/`waiting_for_user`; do not stretch a span across a human wait. Capture
all windows through finalization and submit once. Resume/lifecycle instrumentation,
durable queues, exactly-once delivery and automatic retries are **not** implemented.
An explicit second submission receives a new trace ID. This limitation must be
resolved by the producer before claiming one trace for every real agent run.

The exporter makes one synchronous bounded attempt, with a three-second timeout
per HTTP phase. Call it off the async request loop, using the application's normal
worker mechanism. Keep a bounded backlog if needed. Its failure must never change
a plan, cause a new model call or delay a user retry. Record only the enumerated
result outcome/counts for troubleshooting, never the wrapper or collector body.
The owner must test those producer guarantees when adding the hook.

## Configuration, privacy and delivery semantics

- With no `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `export_run` returns `disabled`
  before inspecting the observation or constructing a client. Setting an endpoint
  alone does not install a hook. Pass `endpoint=""` to disable explicitly even
  when the variable exists. The generic OTLP endpoint/protocol/header variables
  are not supported; only OTLP/HTTP JSON and a complete trace-specific URL.
- An endpoint is trusted server configuration. HTTPS is supported; plain HTTP is
  accepted only for `localhost`, `127.0.0.1` or `::1`. Credentials in URLs, query
  strings, fragments, whitespace and invalid ports are rejected. No redirect,
  ambient proxy, `.env`, global tracer or existing JSONL file is used. Hosted
  collectors needing authentication require a separately reviewed extension;
  do not put tokens in the URL.
- Output is an explicit field projection, not a scrubbed serialization of an
  entire object. No club/run/event/model-trace ID, step text, source, prompt,
  question, answer, URL, member identity, exception message or collector diagnostic
  is copied. Trace/span IDs are fresh random values, not hashes of private IDs.
- Only exact values listed in `PublicLabels` can appear as tool, capability,
  capability version, prompt version or model labels. Defaults export
  `unregistered`. This is a trusted public-label allowlist, **not** a universal PII
  detector. Owners must review those values and must not populate it from input.
- Exported metrics are run status/limits/cost, step number/state/optional timing,
  model-call latency, input/output tokens, cost, retries, replay flag and typed
  status/error code. Currency is USD; cost attributes are decimal strings to
  preserve exact values. They do not establish that a real provider was billed.
- Limits: 64 steps, 256 calls, 1 MiB encoded request, 64 KiB decoded response.
  These are exporter resource limits, not new agent budget limits.
  Responses must use identity encoding (requested explicitly); compression is
  rejected before decoding so a compressed response cannot bypass the bound.
- `accepted` means the collector acknowledged all spans, not durable storage.
  Empty default `partialSuccess` is also accepted (verified with Jaeger 2.23.0).
  Nonzero rejection returns `partial`; zero rejected with a message returns
  `warning`, with the message omitted. Malformed/oversized replies are errors.
  Partial success is never retried. 429/502/503/504 and transport failures are
  marked `retryable` for owner handling; this exporter never retries automatically.

## Evidence and remaining work

The [local proof](evidence/local-proof.json) and [viewer image](evidence/jaeger-synthetic.png)
record the 10 November synthetic demonstration: actual HTTP acknowledgement,
Jaeger API readback, five spans, correct parents and no private-text canaries.
The image was inspected after capture. Readback bytes and temporary browser files
stay in untracked `output/`; the committed summary contains only selected metadata.

Offline regressions: `tests/test_otel_input.py`, `tests/test_otel_payload.py`,
`tests/test_otel_export.py`, `tests/test_otel_demo.py`. These need neither Docker,
a model key nor network. CI runs them through the existing root check.

Remaining acceptance: real producer association/timestamps with a test of its
async/failure behavior; registered public labels; one finalized trace per real run;
C-20 provider validation; hosted deployment/monitoring. No real-run, ASME, billing,
production telemetry, dashboard, alert or bonus-grade outcome is claimed here.
