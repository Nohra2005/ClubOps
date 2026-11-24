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

## 2026-10-22 — Tatiana Nohra, with Claude (feat/contracts-v0.2)

**Did:** Contracts 0.2.0 (D-54): Answer with `ask`/`look_in`; agent run; calendar item; draft; event status and history; contact; asset. New provisional capabilities `plan-event`, `draft`, `calendar-items`; `ask` 0.2.0. Directory store (contacts, assets, events) in the shared/club SQLite files. Schemas regenerated. F-55 to F-60.

**State:** `make check` passes (233 tests). Branch `feat/contracts-v0.2` pushed; PR should carry the `contract-change` label.

**Next:** tell Christophe (UI examples updated to the new fields; `schemas/` is the source of truth) and Joey (`schemas/calendar-items.*`, `schemas/draft.*`). Then T-14 planner agent (needs the API key soon) or T-15 rules.

**Open questions / blockers:** none.

## 2026-10-23 — Tatiana Nohra, with Claude (feat/planner-agent)

**Did:** T-14 planner agent in `src/clubops/agent/` (D-63): `planner.py` (loop, tools, guard rails, prompt `planner-v1`), `rules_check.py` (plain-code rule check until T-15), `runs.py` (runs saved in the club file). 19 tests with a scripted model, plus one through the real model client with a fake provider. F-80 to F-86.

**State:** `make check` passes (284 tests). No recordings yet: a real run needs the API key (record once, then replay for free).

**Next:** T-15 (model-judged rules, approvals, deadlines) and T-16 (proposal draft as a new tool). Web API endpoints /events/plan, /runs/{id}, /runs/{id}/answer can wrap `Planner.start/answer/keep_going` + `RunStore`.

**Open questions / blockers:** API key for recorded runs.

## 2026-10-23 — Tatiana Nohra, with Claude (feat/planner-tools-v2)

**Did:** Planner tools 8 → 6 (D-64): past events folded into search-memory, check-calendar removed; prompt `planner-v2`. Deadlines on AUB holidays move to the day before (`agent/holidays.py`, 2026-27 list). `ClubProfile.kind` (club/society) and `faculty`; contracts 0.2.1, `draft-proposal` 0.1.1. ASME material (4 proposals, 12 expense forms) summarised privately in `clubops-raw/asme/`.

**State:** `make check` passes (300 tests).

**Next:** T-15 rules; ASME test events (T-36).

**Open questions / blockers:** how event spaces are booked (WebReserve confirmed for West Hall; Green Field unknown); academic calendar (exam weeks).

## 2026-10-23 — Tatiana Nohra, with Claude (feat/planner-tools-v2, continued)

**Did:** T-08 rulebook (25 AUB rules with quoted sources, `scripts/build_rulebook.py`, `scripts/load_rulebook.py`); T-15 rule check: code for facts + one model call for description-only triggers (`agent/rules_judge.py`, prompt `rules-judge-v1`); working-day lead times (`Requirement.working_days`), holidays moved to `clubops/holidays.py`. ASME test events (15) drafted privately. D-65; F-88 to F-92. `apply-rules` 0.1.1, `plan-backward` 0.1.1.

**State:** `make check` passes (315 tests).

**Next:** Tatiana reviews the 25 rules; Alexis fills real approvals for ASME; then T-16 proposal draft (both form versions: 33 and 39 questions).

**Open questions / blockers:** none new.

## 2026-10-24 — Tatiana Nohra, with Claude (feat/backend-api)

**Did:** T-22 part 1: FastAPI app (`src/clubops/api/`: `app.py` routes, `security.py` sessions + members + Google sign-in, `store.py`, `views.py`), `docs/api.md` for Christophe, `scripts/add_member.py`. Planner gained `on_step` (progress saving) and re-planning an existing event. D-67; F-93 to F-98. T-10 to T-15 marked done (merged).

**State:** `make check` passes (331 tests). C-13 unblocked.

**Next:** T-17 chatbot (replaces the placeholder `/api/chat/ask`), T-16 proposal, T-18 learning; deploy (T-25) needs `CLUBOPS_SESSION_SECRET` and the Google client id.

**Open questions / blockers:** Google client id (Christophe + Tatiana); API key for real runs.

## 2026-10-29 — Tatiana Nohra, with Claude (feat/learning)

**Did:** T-18 learning: `src/clubops/learning/capture.py` (extract with quote check, match with known facts, injection flags, outdated-document flag, expense-form price list); API routes `/api/chat/teach`, `/api/events/{id}/after-event`, `/api/documents`; Review cards show merges and disagreements with the known fact. D-73; F-109 to F-115. Added python-multipart and openpyxl.

**State:** `make check` passes (376 tests).

**Next:** T-09 seed the Running Club know-how through these inputs; Joey's J-10 calls `Learner.learn` for e-mails; J-15 chatbot answers from what is approved.

**Open questions / blockers:** the API key, to measure extraction quality on real material.

## 2026-11-24 — Tatiana Nohra, with Claude (feat/t46-calendar-connect)

**Did:** T-46 second slice (D-155): `calendar/connect.py` (encrypted key vault, one-use connect proof, reader-access retry list), `CalendarService` connect/disconnect/per-club drain/reader grants, routes `GET /api/calendar/connection`, `POST` and `DELETE /api/calendar/connect`, `GET /api/calendar/callback`, `POST /api/calendar/share-cabinet`; cabinet add/remove queue read-only access. `SyncQueue.pending` and `drain` take an optional club. `cryptography` added to dependencies (it was already in the lock file). Tests `tests/test_calendar_connect.py`; rows F-322 to F-326.

**State:** Passes with a fake Google. Not tried against real Google.

**Next:** Set the Google client values on the host and add the redirect address in Google Cloud; Christophe adds Connect, Disconnect and a status line to the Calendar screen; then one live connect and one cabinet add/remove with a test address.

**Open questions / blockers:** Google cancels keys of apps in Testing mode every 7 days; publish the app or accept reconnecting weekly.
