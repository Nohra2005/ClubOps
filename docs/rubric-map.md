# Rubric map

Where each requirement of the course brief is answered. Status: **in place** (in the repo now), **planned** (with its phase).
Kept current in every PR that changes what a row points to.

| Brief requirement | Where | Status |
|---|---|---|
| **1. Idea, problem & agentic justification (20%)** | | |
| Target user, current workflow, problem | `docs/problem.md`, interview notes in `research/` | planned (Phase 1) |
| Why agentic; what stays deterministic or human | [architecture.md](architecture.md) (three kinds of component), [capabilities.md](capabilities.md) | in place |
| Agentic vs simpler baselines (ablation) | `eval/` ablation: checklist · single prompt · prompt + know-how · full system | planned (Phase 4) |
| **2. Agent performance & evaluation (20%)** | | |
| Baselines, metrics, held-out data, adversarial tests | [eval/README.md](../eval/README.md) | protocol in place; data planned (Phase 1–4) |
| Failures turned into regression tests | [failure-matrix.md](failure-matrix.md), checked by `tests/test_failure_matrix.py` | in place |
| **3. AgentOps & observability (15%)** | | |
| Traces across model and tool calls | `capabilities/runner.py` + `tracing.py` (one record per call, metadata only) | in place |
| Latency, tokens, cost, retries, failures, task success | `TraceMeta`; metrics report in `results/` | fields in place; report planned (Phase 2) |
| Cost per successful task | definition in [eval/README.md](../eval/README.md) | planned (Phase 2) |
| **4. Reliability, QA & security (15%)** | | |
| Retries, timeouts, fallbacks, schema validation, graceful degradation | `capabilities/registry.py` (policy per capability), `runner.py` | in place |
| Authorization, least privilege | `Actor`, club scoping, cabinet-only capabilities, approval gate | in place |
| Secret and PII protection | [knowledge-base.md](knowledge-base.md), `RequesterDetails` (secrets), metadata-only traces | in place (redaction step planned with capture) |
| Prompt-injection defences | `Untrusted`, propose-only capture, flagged proposals | contracts in place; capture planned (Phase 1) |
| Failure Matrix | [failure-matrix.md](failure-matrix.md) | in place (40 rows: 36 covered, 2 partial, 2 planned) |
| Threat model | [threat-model.md](threat-model.md) | in place |
| **5. Software engineering (10%)** | | |
| Modular repo, typing, central configuration, no dead code | `src/clubops/`; ruff + strict mypy in CI | in place (central config planned with the first model call) |
| **6. Poster & demo (10%)** | `docs/demo-script.md` (edge cases shown live) | planned (Phase 4) |
| **7. Documentation & reproducibility (10%)** | | |
| Setup, one-command checks | [README](../README.md), `make check` | in place |
| Reproduce results without API keys | recorded model responses replayed in `make eval` | planned (Phase 2) |
| Architecture and API documentation | [architecture.md](architecture.md), [contracts.md](contracts.md), [capabilities.md](capabilities.md), `schemas/` | in place |
| Data provenance | [data-provenance.md](data-provenance.md) | in place |
| **Bonus: professional practices (up to +10%)** | | |
| CI gates: lint, types, tests, coverage ≥ 85%, schema drift, dependency audit | `.github/workflows/ci.yml` | in place |
| Pull requests, reviews, ownership, branch protection | [CONTRIBUTING.md](../CONTRIBUTING.md), PR template, CODEOWNERS | in place (branch protection to switch on) |
| Dependabot | `.github/dependabot.yml` | in place |
| Evaluation in CI with regression gates | `make eval` in CI | planned (Phase 3) |
| Prompt and model versioning | `TraceMeta.prompt_version`, capability versions | fields in place |
