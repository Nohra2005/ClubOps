# How to assess ClubOps

Prepared 26 November 2026 for C-30, against merged main `4722838`. This is an
evidence route, not a completed independent review or a predicted grade. The final
report (T-27), final evaluation gates (C-22) and fresh setup acceptance (C-29) remain
dependencies. Check the revision and date of every result before using it.

The course brief, `503N_798S.pdf`, page 5, gives the following **suggested weights,
subject to change**. Page 6 requires failures, invalid inputs and security cases in
the application demo. The PDF is supplied separately by the team; it is not copied
into this repository.

## Rubric to evidence

Paths below are relative to this guide. Commands run from the repository root
unless they explicitly begin with `cd web`.

| Rubric item                                                | Evidence to inspect                                                                                                                                                                                                                                                                              | Reproduction or assessment                                                                                                                                                                  | Limit / remaining evidence                                                                                                                                                                                                                                |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Idea, problem formulation and agentic justification (20%)  | [Plan](../docs/plan.md), [architecture and decision boundaries](../docs/architecture.md), [design log](../docs/design-log.md)                                                                                                                                                                    | Follow one event through model-chosen tools, deterministic checks and human revision approval. Compare the baseline protocol in [eval/README.md](../eval/README.md).                        | Interview/time-saving claims need authorized source records. A proposed baseline protocol does not establish a measured benefit.                                                                                                                          |
| Agent performance / research evidence and evaluation (20%) | [Frozen protocol](../eval/FROZEN.md), [model trial](../results/model-trial.md), [chatbot result](../results/chatbot-evaluation.md), [learning review workflow](LEARNING_EVALUATION.md)                                                                                                           | Run the free learning export below and inspect its blank rating columns. Authorized reviewers can use the private datasets and recordings described in [eval/README.md](../eval/README.md). | The model trial uses five practice events. The chatbot result uses one marker and a separate enriched store; Q18 is excluded. Final planning/learning/generalization results must be supplied by their owners.                                            |
| AgentOps and observability (15%)                           | [Report scope and metrics](report/architecture-and-operations.md#cost-reporting-and-observability), [OTLP proof](observability/README.md), [run report tests](../tests/test_run_reports.py), [trace report tests](../tests/test_trace_reports.py), [usage tests](../tests/test_usage_reports.py) | `uv run pytest tests/test_run_reports.py tests/test_trace_reports.py tests/test_usage_reports.py`; optionally reproduce the isolated Jaeger demonstration from its guide.                   | Jaeger evidence is synthetic. Real producer hooks, deployed alerts, provider timing and cost coverage remain separate acceptance work. Missing metrics are unavailable, not zero.                                                                         |
| Reliability, quality assurance and security (15%)          | [Failure matrix](../docs/failure-matrix.md), [threat model](../docs/threat-model.md), [security corpus](../tests/security/CORPUS.md), [HTTP integration tests](e2e/live-api.spec.ts), [Google connection tests](e2e/google-connections.spec.ts)                                                  | `make check`; `cd web` then `npm run test:e2e:http` and `npm run test:e2e:live`. Inspect invalid responses, role/CSRF denial, source warnings, retry and approval-revision cases.           | Browser fixtures and scripted models are not real OAuth or a measured defence-off/on attack rate. Review the scope of each security result.                                                                                                               |
| Software engineering / research quality (10%)              | [Ownership protocol](../AGENTS.md), [contributing](../CONTRIBUTING.md), [schemas](../schemas/), [CI](../.github/workflows/ci.yml), [web workflow](../.github/workflows/web.yml), [container workflow](../.github/workflows/container.yml)                                                        | `make check`; `cd web` then `npm ci` and `npm run check`. Inspect meaningful commits and independent reviews on the PR timeline.                                                            | Historical green runs apply to their revisions. Branch-protection settings and independent reviews require separate verification.                                                                                                                         |
| Poster and live demo / presentation (10%)                  | [Demo script](../docs/demo-script.md), [rehearsal guide](demo/README.md), [rehearsal evidence](demo/evidence/)                                                                                                                                                                                   | `cd web` then `npm run demo:check`; subsequently rehearse the deployed flow with the team, including missing facts, budget limit, hostile input and unauthorized action.                    | The checked synthetic rehearsal and silent recording do not complete the live team demonstration, final narrated backup or poster acceptance.                                                                                                             |
| Documentation and reproducibility (10%)                    | [README setup](../README.md#quickstart), [deployment guide](DEPLOYMENT.md), [API](../docs/api.md), [data provenance](../docs/data-provenance.md), [actual teammate attempt](report/setup-attempt-2026-11-20.md)                                                                                  | Fresh clone: `docker compose up --build`, then local login at `http://127.0.0.1:8080/login`. Follow the check commands below.                                                               | The recorded teammate attempt stopped at the missing Docker engine. A completed fresh README-only setup and final report incorporation are still required. Some root documentation is dated; use current architecture/API entries and versioned receipts. |

## Free local checks

Requires uv/Python 3.11, Node 22.12+ and the documented browser prerequisites. Docker
with Compose 2.24+ is needed only for the complete-app/container path. No production
credentials or private club data are needed for these checks.

```sh
uv sync --locked
make check
```

If Make is unavailable, the equivalent root gates are:

```sh
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy
uv run pytest --cov --cov-report=term-missing
uv run python scripts/export_schemas.py --check
uv run python scripts/tasks.py --check
```

Frontend checks run separately:

```sh
cd web
npm ci
npm run check
npm run test:e2e
npm run test:e2e:http
npm run test:e2e:live
```

See [web setup](README.md#checks) for Chrome/bundled Chromium selection. The demo
and intercepted HTTP suites use synthetic records. The live suite starts an actual
local API and SQLite with a scripted model and dev-only account; it does not call
a paid provider or test production Google consent. The suites have separate ports.
Never point these synthetic mutation tests at the production host.

From the root, export learning evidence to a new private/ignored output path:

```sh
uv run python scripts/eval_learning.py export --cases tests/fixtures/learning.synthetic.csv --as-of 2026-10-29 --model fake-model --dataset-kind synthetic --recordings tests/fixtures/learning-recordings --sheet output/grading-learning-review.csv
```

The last two columns must be blank. A human marks `learned` and `answer_ok` with
yes/partly/no; [the score command](LEARNING_EVALUATION.md#3-build-the-results-table-offline)
then counts ratings offline. Do not generate ratings to manufacture a passing
evaluation. Real sheets, source text and model recordings remain private. The
evaluation protocol's historical `make eval` references are not an implemented
Makefile target; use each documented runner instead.

## Engineering bonus evidence

Page 5 offers up to +10% for demonstrated professional capability and impact,
not the presence of a particular tool. It lists examples and does not prescribe
a fixed number of weekly meetings. Evaluate only the supported practices:

| Practice                                | Inspect / reproduce                                                                                                                                                                                                | Evidence boundary                                                                                                                                        |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Task ownership and reviewed delivery    | [TASKS](../TASKS.md), [Projects guide](PROJECT_BOARD.md), [native board readback](board/evidence/native-fields-2026-11-23.json), PR commits and reviews                                                            | Four Monday dates are owner-reported. Commit summaries are retrospective repository context, not attendance or contemporaneous decisions.                |
| Quality automation and contract drift   | The three workflow files above, root and web checks                                                                                                                                                                | Inspect the latest head's outcomes. Tests passing with replay do not establish model quality.                                                            |
| Reproducible deployment and persistence | [Compose](../docker-compose.yml), [Dockerfile](../Dockerfile), [persistence checker](scripts/check-compose-persistence.mjs), [host receipt](https://github.com/Nohra2005/ClubOps/pull/168#issuecomment-7189560351) | Local container replacement and a healthy deployed candidate are observed; backup restoration and end-to-end signed-in acceptance remain open.           |
| Observability and controlled evolution  | [OTLP demonstration](observability/README.md), scoped reporting tests, [model comparison](../results/model-trial.md)                                                                                               | Distinguish synthetic traces from real measurements and practice-set selection from final held-out evaluation.                                           |
| Evaluation automation / security        | [Learning tests](../tests/test_eval_learning.py), [security corpus](../tests/security/CORPUS.md), dependency audit job                                                                                             | Offline runner regressions are implemented; final model-quality/latency/cost/safety thresholds and measured security rates must have their own evidence. |

[ENGINEERING_EVIDENCE.md](ENGINEERING_EVIDENCE.md) preserves dated receipts and
remaining work. A waiver, a board iteration or an installed tool does not prove
independent review, a meeting outcome or production operation.

## Final review handoff

Before marking C-30 complete:

1. Tatiana links this guide near the top of the root README and reconciles the
   owner-maintained [rubric map](../docs/rubric-map.md) and [evidence ledger](../docs/evidence.md)
   with the final report. Suggested README text:

   ```markdown
   How to assess this project: [rubric, evidence and reproduction](web/GRADING_GUIDE.md).
   ```

2. Owners attach missing results and acceptance records, preserving the conditions
   and denominators. Keep unsupported claims as gaps rather than projected scores.
3. Run a genuinely fresh review against the submitted revision, using the original
   brief and no conversation context. Ask for each rubric item: claim, file/line,
   reproduction result, limitation and missing evidence. Record failures and fix
   them. This guide is not that review, and cannot certify its own completeness.

The last verified hosted candidate is `6749fb0`, distinct from merged main
`4722838`. Open #168 contains its label fixes and receipt. Open #170's cabinet
turnover remains a synthetic prototype pending the server contract in #169; it is
not a live deployment or an evaluated handover benefit. Recheck PR/deployment state
before the final presentation.
