# ClubOps plan: the big picture and how we cover the rubric

Read this first. It says what we are building, how the parts fit, and how each rubric item will be proven. Tasks with owners are in [`../TASKS.md`](../TASKS.md); decisions and reasons in [`design-log.md`](design-log.md). Deadline: **30 November 2026**.

## What ClubOps is

A web app where an AUB club cabinet plans its events. An agent turns "5K run with BLK coffee next Thursday" into the approvals needed, a task plan with deadlines, the OSA proposal and every message draft. While the cabinet works, ClubOps learns the club's know-how (after-event forms, notes, forwarded OSA emails, AUB documents), so next year's cabinet starts with it.

**Rules that never bend** (they are also what makes it safe and gradable):
1. It never invents a rule. Every answer and form field cites its source; when it doesn't know, it says so and names who to ask.
2. It never acts outside the app on its own. Emails, the OSA submission, saving facts to memory and calendar items need a cabinet member's approval.
3. Inside the app the agent is free: it chooses its own steps, asks for missing information and stops at 8 steps or $0.05 per plan.
4. AI costs are kept low: AI runs on a click, results are stored, plain code where it is enough.

## The parts and who owns them

| Part | What it does | Owner | Talks to others through |
|---|---|---|---|
| Memory + approval gate | Learns facts, merges, flags contradictions and outdated documents; Review | Tatiana | contracts in `src/clubops/contracts/` |
| Chatbot | Answers with sources, or "not sure, ask X" | Tatiana | API (UI spec) |
| Event planner agent | Approvals, tasks, deadlines, proposal; asks when information is missing | Tatiana | API; calendar contract |
| Drafter | WhatsApp, emails, captions, poster text, expense form, impact report | Joey (templates), Tatiana (engine) | `Draft` contract (T-13) |
| Calendar + reminders | Google Calendar copy of approved plans; reminders to role holders | Joey | [`calendar-contract.md`](calendar-contract.md) |
| Web app | All screens | Christophe | API in the UI spec |
| Clubs | Shared AUB rules; each club's own know-how; new-club setup (ASME) | Tatiana | contracts |

```
Cabinet ──> Web app (Christophe) ──API──> Backend (Tatiana)
                                            ├─ Planner agent ── rules, memory, past events
                                            ├─ Chatbot ──────── approved facts only
                                            ├─ Learning ─────── Review (human approves)
                                            ├─ Drafter ──────── templates (Joey)
                                            └─ Approved plan ── calendar items ──> Calendar sync (Joey) ──> Google Calendar
```

## Order of work

1. **Before building the agent:** test data written and frozen (T-01 to T-05). Christophe and Joey start in parallel against fake data and the calendar contract.
2. **Core:** model client, redaction, storage, contracts (T-10 to T-13), then planner, rules, proposal, chatbot, learning (T-14 to T-18).
3. **Complete the loop:** handover (C-19), new-club setup (C-21), daily check (J-11), API (T-22), deploy (C-18); frontend connects (C-13, C-14); calendar on the server (J-09).
4. **Prove it:** pilot event (T-32), final evaluation (T-26), evaluation in CI (C-22), docs, poster, demo, grader check (T-27, T-31, T-34).

## Rubric coverage (target 100/100 + bonus)

Each row says what the grader must find, where it will be, and which tasks produce it. Keep [`rubric-map.md`](rubric-map.md) pointing at the real files as they appear.

### 1. Idea, problem and agentic justification (20)

| Grader looks for | Evidence | Tasks |
|---|---|---|
| A real user and a real problem | `docs/problem.md`, consented interview notes, timed walkthrough | T-29 |
| Why an agent, not a form or a checklist | Agent loop that picks its own steps and asks for missing information; `architecture.md` says what stays deterministic or human | T-14, T-31 |
| Agent beats simpler options | Results table: checklist vs plain model vs model + rulebook vs ClubOps | T-06, T-26 |
| Used for real | Pilot event write-up | T-32 |

### 2. Agent performance and evaluation (20)

| Grader looks for | Evidence | Tasks |
|---|---|---|
| Test sets made before the system, held out | `eval/FROZEN.md` with hashes and dates | T-01 to T-04 |
| Baselines and clear metrics | Approvals caught/missed/false alarms, field accuracy, blind 1–5 grades from 3 graders, invented-answer rate, learning test | T-05, T-06, T-26 |
| Honest variance | 3 runs per configuration, spread reported | T-26 |
| Failures become tests | `docs/failure-matrix.md` rows with regression tests | J-13, T-26, J-06 |
| Reproducible numbers | `make eval` from recorded responses, no API keys | T-10, T-26 |

### 3. AgentOps and observability (15)

| Grader looks for | Evidence | Tasks |
|---|---|---|
| Traces across model and tool calls | One trace per call, including each agent step | T-10, T-14 |
| Latency, tokens, cost, retries, failures | Report in `results/`; Settings shows monthly cost | C-20 |
| Cost per successful task | Cost per successful plan in the results | C-20, T-26 |
| Limits enforced | Step and cost limits tested | T-14 |

### 4. Reliability, QA and security (15)

| Grader looks for | Evidence | Tasks |
|---|---|---|
| Retries, timeouts, fallbacks, schema validation | Runner policy per capability (in place); fallbacks shown in the UI | T-10, C-12 |
| Authorization and least privilege | Roles, adviser read-only, club scoping, approval gate | T-18, T-22, C-02 |
| Secrets and personal data protected | Redaction before the model; secrets only on the host; metadata-only traces | T-11, C-18 |
| Prompt injection defended | Untrusted inputs, propose-only learning, adversarial test set, injection success rate measured with defences off and on | T-18, J-13 |
| Failure Matrix and threat model current | Updated to the new scope | J-13, T-31, J-06 |

### 5. Software engineering (10)

| Grader looks for | Evidence | Tasks |
|---|---|---|
| Modular, typed, central config, no dead code | ruff + strict mypy in CI (in place); contracts shared by all parts | all |
| Clear interfaces between parts | Contracts, API table, calendar contract, `AGENTS.md` | T-13, T-22 |

### 6. Poster and demo (10)

| Grader looks for | Evidence | Tasks |
|---|---|---|
| Every poster number backed | `docs/evidence.md`, each claim linked to a result | T-27, T-29 |
| Demo shows edge cases live | `docs/demo-script.md`: missing information, a too-late date, a "not sure" answer, an injected email ignored | T-27 |

### 7. Documentation and reproducibility (10)

| Grader looks for | Evidence | Tasks |
|---|---|---|
| Setup in one command | README; `make setup`, `make check`, `make eval` | T-31 |
| Architecture, API and data provenance | `architecture.md`, `contracts.md`, UI spec, `data-provenance.md` | T-31 |
| A grader can find everything | "How to grade this project" at the top of the README | T-34 |

### Bonus: professional practice (up to +10)

The brief asks for "evidence of use", not tool logos: a few practices done in depth.

| Grader looks for | Evidence | Tasks |
|---|---|---|
| CI gates | lint, strict types, tests with 85% coverage, schema drift, dependency audit (in place); web checks; `make eval` with thresholds | C-23, C-22 |
| Reviewed PRs and branch protection | `main` protected (GitHub Pro from the Student Pack): PR only, 1 review by another teammate, checks green; PRs name their task | T-40, all |
| DevSecOps | Dependabot and pip-audit (in place); gitleaks and a security linter in CI (GitHub secret scanning and CodeQL need a public repo or a paid plan) | J-16 |
| Observability tooling | OpenTelemetry traces of each agent run (viewable in Jaeger or Langfuse), metadata only | C-25 |
| Reproducible environment | Docker Compose for the whole app; Dockerfile and Render config (in place) | C-24, C-18 |
| Production monitoring | Error monitoring on the deployed app (e.g. Sentry free plan), personal data scrubbed, one real caught error shown | C-26 |
| Controlled evolution | Prompt and model versions in every trace; cheap vs stronger model compared with measured quality, latency and cost | T-26 |
| Advanced testing | API contract tests (in place), red-team set with a measured attack success rate | J-13, C-13 |

## Brief checklist (from the course announcement)

| The brief asks | Where we answer it |
|---|---|
| Problem before technology; real user; current workflow | `docs/problem.md`, interview notes (T-29) |
| What stays deterministic or human-controlled | `docs/architecture.md`; approval gate; plain-code rule check and safety rules (T-31) |
| At least one real-world constraint, evaluated | Cost (cheap vs stronger model, cost per plan) and human approval (T-26) |
| Tests beyond the happy path: invalid, ambiguous, tool failure, malformed, rate limit, malicious, unauthorized | `docs/failure-matrix.md` + tests; red-team set (J-13) |
| Memory: scope, lifetime, retrieval, privacy | `docs/knowledge-base.md` (T-31) |
| UI designed around the user, not chat by default | Events, Review, Calendar, Knowledge, Handover screens (done) |
| Final submission: demo + poster, repo, evaluation, traces and metrics, failure and threat analysis, architecture/API docs, technical report | T-26, T-27, T-31, T-34; `traces/samples/`; `docs/api.md` |
| Demo shows edge cases, failures, invalid input and security challenges | `docs/demo-script.md` (T-27) |
| "Not the most features": strong idea, justified choices, credible evidence, known limits | Limitations section in the report and README (T-27) |

## Risks

| Risk | What we do |
|---|---|
| Too much scope for 5½ weeks | Deep and measured: planner approvals, chatbot, learning. Everything else simple but working |
| Teammates go quiet | Their parts have clear contracts; if a task stalls for 3 days, Tatiana takes it or cuts it, and records the cut in the design log |
| Results look worse than the poster | The poster is updated to the new numbers; honest results score better than unproven ones |
| AI costs | Replay mode in tests and CI; limits per plan; cost shown in Settings |
