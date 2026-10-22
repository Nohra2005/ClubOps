# Handoff log — Capture from chats/emails, evaluation datasets

Owner: Tatiana Nohra (since 2026-10-21, D-08; previously Christophe El Chabab). Covers the `capture` capability (turning untrusted chat/email text into know-how proposals), and the evaluation datasets/harness in `eval/`.

See `docs/handoff/TEMPLATE.md` for the entry format. Append new entries at the bottom.

No entries yet — `capture`'s contract (`CaptureRequest`/`CaptureResult` in `src/clubops/contracts/knowhow.py`) and its slot in the registry exist and are contract-tested, but the capability itself isn't implemented. Start your first entry here once you begin.

## 2026-10-21 — Tatiana Nohra, with Claude (feat/model-client-and-redaction)

**Did:** Prepared the first D1 labelling pack: 40 cabinet-chat episodes (6 h silence split, D-17), redacted (D-09 plus links, D-36), selected by a fixed-seed script (D-37). Wrote `eval/d1-labelling-guide.md`. Pack and empty label sheet are in git-ignored `data/private/d1/`.

**State:** Docs only, no code changed. The episode script is a throwaway prep script; the tested parser is step 2.

**Next:** Tatiana labels 5 episodes, calibration check, then the remaining 35. Freeze the hash in `eval/FROZEN.md` before any capture code.

**Open questions / blockers:** Only `cabinet.txt` is on disk so far; members-group, tala-dm, triathlon and presidents chats still need copying into `data/raw/chats/` (presidents chat: only OSA staff messages, D-15). D-36 to D-39 are proposed, awaiting Tatiana.

## 2026-10-22 — Tatiana Nohra, with Claude (chore/team-plan)

**Did:** Scope settled (D-40 to D-49). The 40-episode chat labelling is dropped; evaluation is now the past-events test (21 events drafted in the private `clubops-raw/eval/d5-events.csv`), a 30-question chatbot test and a learning test. Added `TASKS.md`, `AGENTS.md`, `docs/plan.md`, `docs/calendar-contract.md`, `scripts/tasks.py`.

**State:** `make check` passes. Branch `chore/team-plan` pushed, PR to open.

**Next:** T-01 (correct the past-events table), then T-02, T-03.

**Open questions / blockers:** D-36 and D-38 still need Tatiana's OK. T-33 (handover test) keep or drop by 8 November.

## 2026-10-22 — Tatiana Nohra, with Claude (feat/model-client)

**Did:** Built the model client (`src/clubops/model/`): any OpenAI-compatible provider, replay/record/live, schema validation, cost per call, per-plan budget ($0.05, 8 steps). 19 tests on a fake provider; failure rows F-41 to F-46; D-52. Running Club tests frozen (eval/FROZEN.md).

**State:** `make check` passes (135 tests). Branch `feat/model-client` pushed, on top of `chore/team-plan`.

**Next:** T-11 redaction, then T-12 storage, T-13 contract changes. API key from the professor needed only from T-14/T-17.

**Open questions / blockers:** Which provider the professor's key is for; confirm it doesn't train on inputs (D-03).

## 2026-10-22 — Tatiana Nohra, with Claude (feat/redaction)

**Did:** `src/clubops/redaction.py`: hides links (keeps site name), e-mails, AUB IDs, Lebanese and international phones; leaves money ranges, dates, times, prices, distances, CRN alone. 29 tests on made-up data; private check on the real cabinet chat found nothing personal left. Failure rows F-47 to F-50.

**State:** `make check` passes. Branch `feat/redaction` pushed.

**Next:** T-12 SQLite storage, then T-13 contract changes.

**Open questions / blockers:** D-36 (hide links) and D-38 (French) still "proposed": Tatiana to confirm. Standalone AUB usernames not caught (F-50).

## 2026-10-22 — Tatiana Nohra, with Claude (feat/sqlite-store)

**Did:** SQLite storage behind the existing store (`knowhow/backends.py`): memory, single file, and split layout (`general.db` + `clubs/<club>.db`); full-text search (`store.search`). All 20 store tests run on all three backends; 7 new tests (restart, club separation, search, rollback). F-51 to F-54, D-53, ADR 0004 updated.

**State:** `make check` passes (212 tests). Branch `feat/sqlite-store` pushed.

**Next:** T-13 contract changes (not-sure answers, agent runs, event status, calendar items, drafts, contacts, assets, event history + their tables).

**Open questions / blockers:** F-54 (two files, no shared transaction) left as a known limit.
