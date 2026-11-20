# Frontend verification — 22 October 2026

Scope: C-01 through C-12 against the synthetic demo API. C-13 is blocked by T-22. Google OAuth, model calls, real calendar sync, forwarding email and deployment have not been exercised or represented as completed integration.

| Check                                          | Observed result                                                        | Reproduce                                                                                                                                                  |
| ---------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend lint, formatting, strict types, build | Passed                                                                 | `cd web && npm run check`                                                                                                                                  |
| Frontend unit tests                            | 13 passed                                                              | `npm test` in `web/`                                                                                                                                       |
| Real-browser workflows                         | 36 passed, desktop and 375px phone                                     | `npm run test:e2e` in `web/`                                                                                                                               |
| Automated accessibility                        | Passed on 11 main routes at both widths; WCAG 2 A/AA and 2.1 AA checks | Accessibility test within the browser suite                                                                                                                |
| Production npm dependency audit                | 0 reported vulnerabilities                                             | `npm audit --omit=dev`                                                                                                                                     |
| Locked Python dependency audit (C-16)          | No known vulnerabilities after updating `certifi` to 2026.10.19        | Root `uv export --locked --format requirements-txt --no-hashes --no-emit-project --output-file requirements.txt`, then `uvx pip-audit -r requirements.txt` |
| Existing Python suite                          | 116 passed; 93.63% coverage                                            | Root `uv run pytest --cov`, using a workspace temporary directory on this machine                                                                          |
| Existing Python lint/types                     | Passed                                                                 | Root Make targets / equivalent Ruff and mypy commands                                                                                                      |
| Schema and task checks                         | Passed                                                                 | `python -X utf8 scripts/export_schemas.py --check`; `python scripts/tasks.py --check`                                                                      |

Browser workflows cover planning, questions, approval persistence, chat sources/uncertainty/teaching, review batches, second-president state, calendar completion, knowledge edit proposals, handover export/sign-off, member/document management, setup with skipped questions, adviser restrictions, double clicks, offline/error/fallback/empty/loading states and run limits. They use real Chrome with synthetic records and do not incur model charges.

Visual inspection included the event overview and task workspace at desktop and phone sizes, plus the loaded phone Settings layout. Text contrast was corrected after automated checks found low-contrast secondary labels. Browser tests also check horizontal fit of the main routes.

This is frontend evidence, not evidence that the unimplemented backend agent meets its evaluation targets. C-16 fixes the Python dependency-audit failure reported in the project review: Christophe explicitly authorized updating the locked `certifi` package to 2026.10.19. The local audit uses Windows system certificate trust (`uv --system-certs` and `truststore` for `pip-audit`) to verify the network's certificate; TLS verification and vulnerability checks remain enabled. The shared GitHub workflow does not yet run the new frontend checks.

Both existing GitHub jobs passed on security-fix commit `1043c2f`: dependency vulnerability audit and lint/types/tests/contract drift. See [run 39793167497](https://github.com/Nohra2005/ClubOps/actions/runs/39793167497).

## Contract synchronization — 23 October 2026 (C-17)

Merged main through `597685d`, preserving both teams' changes. Canonical main decision IDs D-50–D-54 and failure IDs F-41–F-60 remain unchanged; conflicting unpublished frontend entries now use D-55–D-59 and F-61–F-70. New compatibility cases are F-71–F-75. The initial 22 October results above are historical; current results follow.

| Check                               | Observed result                                                                                                 | Reproduce                                                                              |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Frontend quality gates              | Passed; 33 unit tests, lint, formatting, strict types and production build                                      | `cd web && npm run check`                                                              |
| Existing demo browser workflows     | All 36 cases verified: 34 passed initially; the two chat cases passed after removing duplicate uncertainty text | `npm run test:e2e`; targeted recheck: `npm run test:e2e -- e2e/chat.spec.ts`           |
| HTTP contract browser workflows     | 8 passed, desktop and 375px phone                                                                               | `npm run test:e2e:http`                                                                |
| Merged Python suite                 | 233 passed; 95.18% coverage                                                                                     | Root `uv run pytest --cov`, with a fresh workspace temporary directory on this machine |
| Merged lint/types, schema and tasks | Passed; Ruff formatting for 56 files and mypy for 35 source files                                               | Root Make targets / equivalent commands; UTF-8 schema check on Windows                 |

HTTP checks use the actual fetch transport and screen components with intercepted synthetic responses. They do not prove that T-22, Google authentication, calendar sync or deployment are complete. `API_NOTES.md` records the confirmed mappings and remaining response/route agreements. The Windows command-runner account became unavailable during verification; the isolated port-5174 test server needed explicit cleanup before Playwright returned its successful result. The existing demo preview on port 5173 was preserved.

## Available API integration — 26 October 2026 (C-13 / C-19 / C-20 / C-18)

The earlier sections are historical. Current checks use T-22 part 1 and the assigned
handover/report endpoints. No real club data, Google account, paid model or hosting
service was used.

| Check                         | Observed result                                                                                                         | Reproduce                                                                                                                                   |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend quality gates        | Passed; 38 unit tests, lint, formatting, strict types and static build                                                  | `npm run check`                                                                                                                             |
| Existing demo browser suite   | 36 passed on desktop and 375px phone, including accessibility                                                           | `npm run test:e2e`                                                                                                                          |
| Isolated HTTP browser suite   | 18 passed; synthetic intercepted responses, including GIS exchange/failure, logout, continuation and missing telemetry  | `npm run test:e2e:http`                                                                                                                     |
| Real local API flow           | 2 passed; cookie login, planning, approval, calendar, reload, handover, usage, logout                                   | `npm run test:e2e:live`                                                                                                                     |
| Production static/router flow | 4 passed using built HTTP-mode assets, Caddy and real local API; includes deep links, JSON errors and missing assets    | Set `VITE_API_MODE=http`, build, then `npm run test:e2e:production`                                                                         |
| Root Python tests             | 343 passed; 93.33% coverage                                                                                             | `uv run pytest --cov --cov-report=term-missing`                                                                                             |
| Root quality gates            | Ruff check/format passed (96 files), strict mypy passed (58 source files), schemas/tasks passed                         | `make check` equivalents; `python -X utf8 scripts/export_schemas.py --check` on Windows                                                     |
| Deployment configuration      | Caddy validation and Bash syntax passed; `render.yaml` validates against Render's official JSON Schema                  | `caddy validate --config web/Caddyfile --adapter caddyfile`; `bash -n web/start.sh`; schema at `https://render.com/schema/render.yaml.json` |
| Report CLI                    | Exported two actual scripted browser runs: 8 planner steps and $0.008 **synthetic charged cost**, no trace measurements | `python -m clubops.reports --data-dir <temporary-fixture-store> --club running-club --month 2026-10 --output output/usage.synthetic.json`   |

Live suites use a new temporary SQLite store under root `output/`, synthetic cabinet
members, dev-only login and the API owner's scripted planner. They make no model calls.
Production routing tests use the same Caddyfile as the image; Caddy 2.11.7's downloaded
Windows binary was checked against the official release SHA-512 checksum. The full Docker
image has **not** been built because the local Docker engine is stopped. These checks do
not establish Render persistence, provider latency/token measurements or real OAuth login.

One intermediate root run failed because a browser evidence row used the Python-only
`covered` classification. Commit `f011231` applies the existing `frontend covered`
convention; the complete root suite then passed. GitHub checks for the subsequent
packaging and hosting-preparation commits passed. Shared CI still has no frontend job;
the browser results above were run locally.

The demo on `http://127.0.0.1:5173` remains available. Current task status and external
blockers are in `TASKS.md`, `API_NOTES.md` and `DEPLOYMENT.md`.

## Engineering bonus and learning integration — 1 November 2026

Pulled main through `d1a6a86`. New work is in PR #44 under the updated reviewed-PR /
merge-commit protocol. Coordination and teammate-agent instructions are in issue #43.
The course bonus section is page 5; page 6 requires realistic failure/security demos.

| Check                          | Observed result and reproduction                                                                                                                                                                                  |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Root gates                     | Ruff check/format (103 files), strict mypy (62 source files), schema/tasks pass; 388 tests, 92.77% coverage with workspace temporary storage                                                                      |
| Frontend gates                 | `npm run check`: lint, format, 40 unit tests, strict types and production build pass                                                                                                                              |
| Demo / intercepted HTTP        | 36 demo cases and 20 HTTP cases pass at desktop/375px; new warning test excludes instruction/outdated cards from batch approval                                                                                   |
| Live API / development sign-in | 4 cases pass using temporary SQLite, a scripted model and the explicit local form; unknown cabinet email is rejected                                                                                              |
| Actual Compose image           | 4 browser login/routing cases pass against the built app; both production and local targets build                                                                                                                 |
| Volume persistence             | `web/scripts/check-compose-persistence.mjs` creates synthetic state, replaces the container and confirms the state and old session survive; removes its check record                                              |
| Context/privacy                | Actual BuildKit export excludes synthetic environment/node_modules canaries, runtime/private data and host caches; the production image excludes the temporary CA mount, local entrypoint and workspace output    |
| Production guards              | Insecure dev cookie settings are refused before serving; a production build with `VITE_DEV_LOGIN=1` fails deliberately                                                                                            |
| GitHub evidence                | Web quality/browser gates passed in run `41332905874`; clean Linux container/persistence/auth checks passed in `41333987152`; Python/audit passed in `41333987085`. The PR Checks tab identifies the current head |

**Open failure, not a clean production-flow pass:** a local Caddy/API run had four
passing assertions but emitted `sqlite3.InterfaceError` from the session member lookup.
A focused desktop repeat then failed the usage-screen assertion with the same server
error. Issue #45 refers this backend-owned finding to Tatiana, with reproduction,
ignored `output/production-observation.log` and browser trace evidence. No backend fix,
Windows-only conclusion or production-flow completion is claimed. C-13 stays open.

The new Web gate also caught a later `API_NOTES.md` formatting mistake; it was corrected
with Prettier rather than disabling the check. Local network CA trust is supplied only
as an optional BuildKit secret, with TLS verification enabled. Clean GitHub Linux builds
use normal trust and need no local certificate file.

The verified Compose instance is left at `http://127.0.0.1:18080/login` (isolated
`clubops-bonus-check` project, synthetic `president@example.com`). This is the real
local API with dev sign-in, not the browser-storage demo. It has no configured real
Google identity or provider evaluation; new planning needs recordings/provider setup.
Public hosting, OTel export, deployed monitoring, real measured cost/quality, branch
protection and weekly sprint history have not been represented as complete.

## 3 November 2026 — C-21/C-31, PR #55

This branch starts from main `d5dfb17` and is independent of the still-open C-27
PR #54. Test totals therefore describe this branch, not the union of both PRs.

| Check             | Observed result                                                                                                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Root gates        | Ruff check/format: 125 files; strict mypy: 73 source files; schema/task checks pass; 439 tests, 92.99% coverage                                                         |
| Setup regressions | 18 synthetic cases: service/router/real-auth/SQLite checks and one unresolved stale-tab reproduction (F-151); no automatic approval                                     |
| Frontend          | `npm run check` passes: lint, format, 42 unit tests, 12 board-tool tests, strict types and production build                                                             |
| Setup browsers    | 4 demo cases and 6 intercepted HTTP cases pass across desktop and phone: completion, skip/resume, reload, failed/malformed responses and adviser access                 |
| Board preview     | Default dry run reads all 77 main tasks and proposes four seven-day iterations; exact source commit and input hash recorded in ignored `output/project-board-plan.json` |
| GitHub schema     | Current Projects field/view/iteration inputs checked by authenticated public introspection; this does not establish live-board access or successful publication         |

Actual API/SQLite tests explicitly replace the placeholder in a test app; main's
production setup route remains 501 until Tatiana wires the callbacks and `/me`
completion field. Decided-card retry semantics and sourced ASME facts remain owner
integration work. See [CLUB_SETUP.md](CLUB_SETUP.md).

The Projects token still lacks access; the browser host is unavailable. No board,
team access or completed weekly review was fabricated. Board API tests use a stateful
synthetic double (including 123 paginated cards), not live GitHub mutations. See
[PROJECT_BOARD.md](PROJECT_BOARD.md) for the concrete publishing command and limits.
Final-head CI is recorded on [PR #55](https://github.com/Nohra2005/ClubOps/pull/55);
independent review and a merge commit are required before merge.

For the earlier SQLite finding above: #45 was closed by Tatiana's #47. The 2 November
recheck recorded with PR #54 passed all four Caddy/API cases without server exceptions.
That supersedes the older unresolved note; public deployment still remains open.

## 9 November 2026 — C-21/C-31/C-29 follow-up (PR #55)

Synced main `4b3f17e` independently of #54. Root gates pass: **530 passed, 1 skipped;
92.73% coverage**, Ruff/format (132 files), strict types (75 files), schema/task checks.
All **20 setup cases** pass, including returned failed-source results with/without
partial proposals: no progress/queue writes survive and an explicit retry succeeds.
Shared-rule integration checks now follow the current 27-rule sourced rulebook.
Frontend `npm run check` passes with **42 units, 12 board-tool tests**, lint/format/
types/build. Current-main board dry run reads **85 tasks**, without remote writes.

Tatiana accepted F-151's one-tab setup limit and requested #55 leave draft for her
API wiring. Setup production registration and /me are still not wired by this PR.
D-102/F-174 record the compatibility/failure fix. Existing board/admin access and
Wednesday cadence come from her #43 reply; scope still prevents live inspection.
No duplicate board, altered manual cards, completed sprint or private data is claimed.

**9 November final onboarding copy check:** setup now states to use one tab and that no chat history is required (D-103). Repeated frontend check passes (42 units, 12 board-tool tests, lint/format/types/build), and all four existing desktop/phone setup browser flows pass. Projects scope is now enabled, but full discovery returns no visible existing board; direct board URL/access is still required.

## Merged progress and learning evaluation — 2 November 2026 (C-27)

Pulled main `d5dfb17`: PR #44 is merged with the original 17 commits preserved, and
main's Web/Container/Python workflows pass. Tatiana's PR #47 fixes issue #45 with a
shared-connection lock and F-131 concurrency regression. Re-running the previously
failing Caddy/API suite now gives **4 passed**, with no ASGI/SQLite exceptions in
`output/sqlite-fixed-flow.log`. C-23/C-24 are done; deployed C-13 remains open.

C-27 is proposed in PR #54. The scorer depends on published contracts; its assigned
CLI composes the public learner/store/ask interfaces in new per-case sandboxes.

| Check              | Result                                                                                                                                                           |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Root gates         | Ruff check/format (127 files), strict mypy (73 source files), schema/task checks pass; 441 tests, 92.99% coverage                                                |
| CLI typing         | `mypy scripts/eval_learning.py` passes in addition to the package gate                                                                                           |
| C-27 regressions   | 20 synthetic tests: CSV/alias validation, scope/current facts, duplicates, errors/failed spend, label privacy, real record/replay and checked-in offline example |
| Actual offline CLI | The documented fixture command runs without a key/network, with 2 completed cases, 1 expected/learned fact, 1 supported new-fact citation and 0 errors           |
| Frontend           | `npm run check` passes, including all 40 unit tests; no app-screen behavior changed by C-27                                                                      |

The fixture response/token values are synthetic and the replay budget cost is zero.
Neither is a provider-quality or operating-cost result. Reports expose mode, model,
configured token rates, scoring version and the exact dataset-snapshot hash, but no
source/fact/answer text or raw errors. Runtime errors return a nonzero status rather
than becoming valid zero-quality measurements. Explicit mappings support frozen
plain-text labels without rewriting their CSV.

Use [LEARNING_EVALUATION.md](LEARNING_EVALUATION.md) for the exact command, metrics
and limits. The replay regression runs automatically in root CI; real private-set
results and final held-out thresholds remain T-26/C-22. Alias sets must not be tuned
after seeing model outputs. Sandbox verification is simulation, not user acceptance.

## 3 November 2026 — C-27 human review revision

Tatiana's feedback replaces automatic exact-word grading for learning/answer quality
with the two-command workflow in [LEARNING_EVALUATION.md](LEARNING_EVALUATION.md).
The new CSV deliberately contains the private expected/saved facts, question and
actual answer; only learned/answer_ok start blank. Keep real sheets and companions
in ignored private locations. Result Markdown/JSON remains free of evidence text.

Verified after updating to main `22c4dae` and its locked dependencies:

- Root gates pass: Ruff check/format (128 files), strict package typing (73 source
  files), explicit CLI typing, schema/task checks; **469 tests, 92.93% coverage**.
- **48 C-27 tests** cover actual record/replay, a paraphrased saved fact accepted by
  supplied human yes labels, blank/invalid grades, row completeness/provenance,
  literal spreadsheet text, output protection and a model/configuration-free scorer.
- Frontend `npm run check` passes, including 40 units, lint/format/types/build.
- The documented synthetic replay actually produced two review rows, zero errors
  and both rating columns blank. No API key/network or real provider charge was used.
- Linux CI caught a test relying on the local Windows temporary-folder location;
  the regression now sets an explicit repository boundary without weakening the guard.

Earlier exact-label totals above are historical **smoke diagnostics**, not semantic
learning/answer accuracy. They now require the explicit `smoke` subcommand. D-87 and
F-152–F-159 record the revised design/failure evidence. No real private case, actual
human-study grade or T-26 result is claimed. Final-head CI/review is on PR #54.

## 9 November 2026 — frozen learning CSV compatibility (C-27)

Synced main through `4b3f17e` and addressed Tatiana's #54 review: shared source/expected
`fact`, original `l_id`, separate `later_question`, and all three `taught_by` aliases.
The input bytes are unchanged. Unknown types still produce sanitized errors. Three
synthetic cassettes were deliberately refreshed through MockTransport for current
learner prompts; replay remains network-forbidden and ratings remain blank.

- C-27: **70 tests pass**, including full frozen-header record/replay for each alias.
- Full root gates pass: **580 passed, 1 skipped; 92.69% coverage**; Ruff/format
  (135 files), strict package typing (75 source files), CLI typing, schemas/tasks.
- Frontend `npm run check` passes with **40 units**, lint/format/types/build.
- No real private CSV, human-study result or paid provider call was used.

D-101/F-172/F-173 document the regression evidence. Tatiana's re-review and final-head
GitHub checks remain on #54; earlier dated counts above are historical.

**After #54 merged on 9 November:** #55 now contains main 4bed33c and both task histories. Shared evidence/handoff conflicts preserve all entries. Combined root gates pass: 600 passed, 1 skipped, 92.68% coverage; Ruff/format (138 files), strict package types (76 files), CLI typing, schema/task checks. Frontend check passes with 42 units and 12 board-tool tests. Remote checks for the new merge head are on #55; previous 3e0180a had all five green. No production setup wiring or real private evaluation is implied.

## 10 November 2026 - C-33 starter checklist

Based on main 106baa7 independently of #75. Root gates pass: 600 passed, 1 skipped,
92.68% coverage; Ruff/format (138 files), strict types (76 files), schemas/tasks.
Frontend check passes with 48 units, 12 board-tool tests and build.

Actual focused browser checks: 6 HTTP starter cases (explicit/no-auto upload,
malformed/503 retry, rapid double click, cabinet action and malformed cabinet list)
and 6 demo/setup cases, including complete/reloaded starter checks, pending Review,
unverified documents, accessibility and phone width. Default Playwright outputs
collided when suites were run concurrently; the stable demo suite was rerun alone
and all 6 passed. Run the commands in STARTER_CHECKLIST.md sequentially.

D-105/F-179-F-182 record the privacy/completion boundaries. Metadata-only local ticks
never set server setup_complete or approve knowledge. Actual C-21 wiring and deployed
new-club/ASME verification remain open. No private source or paid model call. These
numbers do not include the independent C-34 branch's frontend additions.

## 10 November 2026 - C-34 shared Review guards

Current main 106baa7 plus C-34 passes all local root gates: **600 passed, 1 skipped,
92.68% coverage**, Ruff/format (138 files), strict mypy (76 source files), schemas/tasks.
`npm run check` passes with **46 frontend units, 12 board-tool tests** and build.

Actual browser verification: **8 HTTP review cases**, **2 persistent-demo review
cases**, and **2 accessibility cases covering 11 routes each** on desktop/375px phone.
Tests cover shared facts with ordinary type, source quotes/missing evidence/literal
HTML-like text, all disagreements first, explicit true/false decisions, non-president
restrictions, 403 edit/choice retention and no batching of unsaved scope changes.
The demo now matches T-41's single-president shared approval; historical waiting
responses remain display-compatible.

D-104/F-175-F-178 and `REVIEW_GUIDE.md` record behavior and limits. Existing public
`tests/test_shared_layer.py` runs in root checks; no backend code/contracts changed.
HTTP UI checks use synthetic intercepted responses, not a deployed service or user
study. Final-head CI and independent teammate review are on the C-34 PR.

## 2026-11-20 - C-31 existing board refresh on merged Inbox baseline

Merged main `e4090c6`; shared failure rows preserved once. Live board #4 read-back
verifies 92 merged tasks, 0 new cards and 93 managed field/body updates. Repeat full
sync creates/updates zero. Original 3 manual cards, human fields and status-column
view #8 are preserved. Dated proof is board/evidence/refresh-2026-11-20.json.

Web quality/build passes: 68 units, 32 board-tool tests, lint/format/types.
Branch-local shared docs/tasks: 10 pass. Python source/tests/scripts/schemas/lock
match the final C-35 tree whose root gates pass (710 tests, 93.14%, Ruff/format
162 files, mypy 85 files, schemas/tasks). No application source changed in this
refresh. C-31 remains doing: three genuine weekly-review records are still needed.
No meetings, unmerged task completion or deployed/provider evidence is invented.
