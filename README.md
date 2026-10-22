# ClubOps

> **Team and AI assistants, start here:** [`AGENTS.md`](AGENTS.md) (protocol) · [`docs/plan.md`](docs/plan.md) (big picture and rubric coverage) · [`TASKS.md`](TASKS.md) (who does what; `make tasks WHO=<name>`).

**An AI agent that keeps a student club's know-how alive across cabinet handovers, and uses it to prepare the club's event paperwork.**

EECE 503N / 798S Agentic Systems · American University of Beirut · Fall 2026
Tatiana Nohra · Christophe El Chabab · Joey Saade

## The problem

AUB club cabinets are volunteers who change every year. How things actually get done (which form, how far ahead, who to call, what went wrong last time, why a decision was made) lives in old WhatsApp chats and people's heads, and leaves when they graduate. Meanwhile every event needs a 33-question OSA proposal, a venue booking, an Expense Form, sponsor confirmations and reminders, and small mistakes get submissions sent back.

## What ClubOps does

- **Captures know-how** from the club's chats, handover material, retrospectives and OSA emails. The model proposes; a cabinet member verifies. Nothing is learned silently.
- **Builds handover packs** per role, every line citing its source, after interviewing the outgoing officer about the gaps it finds.
- **Prepares event packets**: works out which AUB rules apply, drafts the proposal form, plans deadlines backward from the event date, and surfaces the club's own lessons at the moment they matter.
- **Never acts alone.** Every email, submission and invite waits for an approval bound to its exact content.

Start with [docs/architecture.md](docs/architecture.md). Contracts: [docs/contracts.md](docs/contracts.md) and the generated [docs/capabilities.md](docs/capabilities.md).

## Quickstart

Requires [uv](https://docs.astral.sh/uv/).

```bash
make setup     # install from the lockfile
make check     # lint, strict types, tests + coverage, contract drift
```

## Status

| Phase | Dates | Scope | State |
|---|---|---|---|
| 1. Foundations | Oct 5–18 | Contracts, knowledge store with verified writes, validators, planner, approval gate, handover assembly, tracing; capture and intake; evaluation sets labelled and frozen | contracts and deterministic core done |
| 2. Core agent | Oct 19–Nov 1 | apply-rules, draft-proposal, surface, ask, find-gaps, handover interview; replayable evaluation; first results | |
| 3. Continuity & pilot | Nov 2–15 | Simulated turnover and three-way handover test on real Running Club history; sponsor replacement; feature freeze Nov 15 | |
| 4. Hardening | Nov 16–30 | Red-team, Failure Matrix regression suite, held-out evaluation, report, demo (Nov 30) | |

## Documentation

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

All real data comes from one club, the AUB Running Club. The agentic capabilities are specified and contract-tested, but not yet implemented.
