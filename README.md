# ClubOps

> **Team and AI assistants, start here:** [`AGENTS.md`](AGENTS.md) (protocol) · [`docs/plan.md`](docs/plan.md) (big picture and rubric coverage) · [`TASKS.md`](TASKS.md) (who does what; `make tasks WHO=<name>`).

**An AI agent that keeps a student club's know-how alive across cabinet handovers, and uses it to prepare the club's event paperwork.**

EECE 503N / 798S Agentic Systems · American University of Beirut · Fall 2026
Tatiana Nohra · Christophe El Chabab · Joey Saade

## The problem

AUB club cabinets are volunteers who change every year. How things actually get done (which form, how far ahead, who to call, what went wrong last time, why a decision was made) lives in old WhatsApp chats and people's heads, and leaves when they graduate. Meanwhile every event needs a 52-question OSA proposal (including conditional sections), a venue booking, an Expense Form, sponsor confirmations and reminders, and small mistakes get submissions sent back.

## What ClubOps does

- **Captures know-how** from the club's chats, handover material, retrospectives and OSA emails. The model proposes; a cabinet member verifies. Nothing is learned silently.
- **Builds handover packs** per role, every line citing its source, after interviewing the outgoing officer about the gaps it finds.
- **Prepares event packets**: works out which AUB rules apply, drafts the proposal form, plans deadlines backward from the event date, and surfaces the club's own lessons at the moment they matter.
- **Never acts alone.** Every email, submission and invite waits for an approval bound to its exact content.

Start with [docs/architecture.md](docs/architecture.md). Contracts: [docs/contracts.md](docs/contracts.md) and the generated [docs/capabilities.md](docs/capabilities.md).

## Quickstart

### Run the complete app locally

Requires Docker with Compose 2.24+ (no Google account or model key needed for local sign-in):

```sh
docker compose up --build
```

Open **http://127.0.0.1:8080/login** and choose **Sign in locally**, using the synthetic
`president@example.com` account. The local target runs the real API and SQLite; it
stores data and a random local session key on a named volume. It binds to loopback.
This is a development setup; public deployment uses the separate production target.

Copy `.env.example` to ignored `.env` only when configuring a provider or recordings.
Replay is the default: reading screens/signing in needs no provider calls, while a new
model-generated plan requires a matching recording or deliberate provider setup.
`docker compose down` stops the app and retains its volume. See
[deployment and proxy trust setup](web/DEPLOYMENT.md) for production requirements,
optional local CA configuration, checks and storage limits.

### Work without Docker

Requires [uv](https://docs.astral.sh/uv/) for Python and Node 22.12+ for `web/`.

```bash
make setup     # install from the lockfile
make check     # lint, strict types, tests + coverage, contract drift
```

Frontend commands and the local API setup are in [web/README.md](web/README.md) and
[docs/api.md](docs/api.md). New [web](.github/workflows/web.yml) and
[container](.github/workflows/container.yml) checks are proposed in PR #44; their
verified runs and remaining bonus work are tracked in [the engineering evidence](web/ENGINEERING_EVIDENCE.md).

## Status

Updated 31 October 2026. Deadline: 30 November 2026. Live task list: [`TASKS.md`](TASKS.md) (`make tasks`).

**Built and tested** (`make check`: lint, strict types, 388 tests, contract drift, dependency audit)

| Part | What works | Where |
|---|---|---|
| Contracts | Shared data shapes for every part, exported as JSON schemas (version 0.2.1) | `src/clubops/contracts/`, `schemas/` |
| Model client | Any OpenAI-compatible provider (the course's OpenRouter key); replay, record and live modes; cost limit per plan | `src/clubops/model/` |
| Privacy | Phone numbers, AUB IDs, e-mails and links hidden before any text reaches the model | `src/clubops/redaction.py` |
| Club memory | Shared AUB file + one file per club (SQLite, full-text search); every fact versioned, nothing saved without a cabinet member's approval | `src/clubops/knowhow/` |
| AUB rulebook | 25 rules from the OSA and AUB documents, each quoting its source, reviewed by the Running Club president | `data/rulebook/aub-rules.json` |
| Planning agent | The model picks its next step from 6 tools; code refuses unsafe steps; asks when facts are missing; stops at 8 steps or $0.05 | `src/clubops/agent/` |
| Rule check and deadlines | Plain code for the facts, one model call for what only the description says; deadlines in working days, moved off AUB holidays | `src/clubops/agent/`, `src/clubops/holidays.py` |
| Learning | Chat teaching, the after-event form and uploaded documents become proposed facts in Review; invented quotes dropped; hidden instructions flagged; old documents flagged; expense forms become a price list | `src/clubops/learning/` |
| Backend API | Google sign-in, events, agent runs, plan approval, tasks, calendar items, knowledge, review, cabinet, handover, usage | `src/clubops/api/`, [`docs/api.md`](docs/api.md) |
| Web app | Every screen of the UI spec, connected to the API | `web/` |
| Handover and cost report | Role guides from approved facts with gaps and who to ask; cost and trace report | `src/clubops/api/handover.py`, `src/clubops/reports/` |
| Evaluation runner | Checklist, plain model, model + rulebook and ClubOps scored the same way (approvals caught, missed, false alarms, cost); ClubOps only sees facts from earlier events | `src/clubops/evaluation/`, `scripts/eval_plans.py` |
| Calendar and drafts (first version) | Calendar items from an approved plan, Google sync with retries, WhatsApp drafts | `src/clubops/calendar/`, `src/clubops/drafts/` |

**In progress**

| Part | Owner | Task |
|---|---|---|
| Deployment (one free host for app and API) | Christophe | C-18, C-14 |
| Google Calendar on the deployed app, reminders, draft templates | Joey | J-01 to J-09 |
| Chatbot with sources | Joey | J-15 |
| Proposal form draft | Joey | J-12 |
| New-club setup, ASME as the second club | Christophe | C-21 |
| OSA e-mail inbox, daily checks, security tests | Joey | J-10, J-11, J-13 |
| ASME test events (waiting for the real approvals) | Tatiana | T-35 |

**Still to do:** seed the Running Club's know-how (T-09); run the baselines once the course key and labels are in (T-06); the final evaluation on past Running Club and ASME events, with the course key (T-26); real pilot event (T-32); report (T-27), poster (J-18), demo (C-28); test runners for the chatbot and learning tests (J-17, C-27).

## Documentation

Learning evaluation (C-27): [offline command, CSV mappings and metric limits](web/LEARNING_EVALUATION.md).
The checked-in replay example uses only synthetic data and no API key; real private-set results remain T-26.

| | |
|---|---|
| [Architecture](docs/architecture.md) | Components, agentic vs deterministic vs human, trust boundaries |
| [Contracts](docs/contracts.md) · [Capabilities](docs/capabilities.md) | Schemas, validation, authorization, error behaviour |
| [Knowledge base](docs/knowledge-base.md) | What know-how is; scope, lifetime, retrieval, privacy |
| [Failure Matrix](docs/failure-matrix.md) · [Threat model](docs/threat-model.md) | Failures and their regression tests; threats and mitigations |
| [Evaluation](eval/README.md) | Datasets, baselines, metrics, held-out protocol |
| [Data provenance](docs/data-provenance.md) | Where data comes from, consent, redaction |
| [Rubric map](docs/rubric-map.md) · [Evidence ledger](docs/evidence.md) | Where each course requirement and each claim is backed |
| [Decisions](docs/adr/) · [Contributing](CONTRIBUTING.md) | Why things are the way they are; how we work |

## Limitations

Most real data comes from one club, the AUB Running Club; ASME (an engineering society) is the second, with less data. Model answers are tested with scripted and recorded answers; quality with a real model is measured in the final evaluation (T-26).
