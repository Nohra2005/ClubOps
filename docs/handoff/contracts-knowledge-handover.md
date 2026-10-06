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
