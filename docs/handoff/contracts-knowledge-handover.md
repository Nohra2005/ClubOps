# Handoff log — Contracts, knowledge base, handover

Owner: Tatiana Nohra. Covers `src/clubops/contracts/`, `capabilities/registry.py`, `capabilities/runner.py`, `knowhow/`, the five ADRs, and the handover capabilities (`build-handover`, `plan-interview`).

See `docs/handoff/TEMPLATE.md` for the entry format. Append new entries at the bottom.

```
## 2026-10-06 — Tatiana (PR #1, feat/contracts-and-core)

**Did:** Built the whole contracts-first foundation: all contract models (common, knowhow, handover, event, club, forms, rules, planning, approvals, sponsors), the 12-entry capability registry, the runner, the knowledge store with verified-write semantics, the deterministic capabilities (validate, plan-backward, approve, build-handover, gap-detection fallback), the OSA form data file, schema/docs generation, the five ADRs, the Failure Matrix (34 rows) with a test that checks it against real test functions, the evaluation protocol doc, and CI (lint/types/tests/schema-drift + dependency audit). 93 tests passing, ~94% coverage.

**State:** Pushed, PR #1 open against `main`, both CI checks green. Not yet reviewed or merged — needs a teammate's approval per `CONTRIBUTING.md` before it can land. `main` currently only has the README stub.

**Next:** Get PR #1 reviewed and merged first — Christophe and Joey's areas (capture/evaluation, event packet) both build directly on these contracts, so nothing else should branch off `main` until this lands. After merge: start on `capture` and `plan-interview`'s agentic implementations (currently only contract-tested, not implemented), and start collecting/labelling real AUB Running Club chat history for the evaluation sets, per the "labels before systems" rule in `eval/README.md`.

**Open questions / blockers:** `suggest-replacement` and the sponsor contracts are still marked provisional (v0.0.1) — they may change once real sponsor-history data shapes it. The Expense Form (separate from the 33-question OSA proposal form) isn't modelled yet at all; flagged in `docs/evidence.md` as an open gap, not yet assigned to anyone.
```

```
## 2026-10-12 — Tatiana, with Claude (fix/core-integrity)

**Did:** PR #1 squash-merged into main (no teammate review; branch protection is unavailable on a free private repo). Fixed four core bugs found by probing, each with a failing-first regression test and a Failure Matrix row (F-35 to F-40): (1) verify now trusts only the queued proposal, so a request can't swap content or drop injection flags under the same id, and a refused decision leaves the proposal queued; (2) the runner scopes every `club_id` anywhere in a request (apply-rules, draft-proposal, plan-backward were unscoped), with a test requiring every request type to name its club; (3) the runner now runs a supplied fallback after retries or on budget_exceeded (result marked degraded), discards attempts slower than policy.timeout_s, and sums tokens/cost over every attempt; (4) an accepted contradiction that reuses the loser's id becomes its next version instead of a duplicate v1. F-08 and F-17 reworded to match what is actually enforced. `ReplacementRequest` gained `club_id` (provisional, suggest-replacement 0.0.1 -> 0.0.2).

**State:** `make check` green locally (108 tests, 93% coverage). Pushed as `fix/core-integrity`, PR open against main. The old `feat/contracts-and-core` branch still exists on GitHub; delete it from the merged PR page.

**Next:** Build the model client layer (central config from `.env`, one client that validates output against the contracts and raises CapabilityError with usage attached, record/replay cassettes, per-packet budget that raises BUDGET_EXCEEDED). Every agentic capability plugs into it, and it closes F-34. In parallel (human, not code): export Running Club chats and record consent, so D1/D5 can be labelled and frozen before capture/intake are written.

**Open questions / blockers:** The runner's timeout check discards late answers but cannot interrupt a running call; the model client must set its HTTP timeout from the policy. A `ValidationError` raised directly by a capability still loses that attempt's usage; the model client should catch it and re-raise as MALFORMED_MODEL_OUTPUT with usage. Fallbacks are passed per call (`run(..., fallback=...)`); each agentic capability should ship its fallback function next to it.
```
