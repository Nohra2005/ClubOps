# Engineering bonus: evidence and remaining work

## Current scope update: 26 November 2026 (C-29/C-30)

This update supersedes availability claims in the dated history below. Main
`4722838` includes setup wiring, expiry/review guards, the UI cleanup and Calendar/Gmail
connection controls (#160/#161/#167). The last inspected Azure candidate `6749fb0`
and its limits are recorded in the [report draft](report/architecture-and-operations.md#hosted-verification-24-to-26-november)
and [host receipt](https://github.com/Nohra2005/ClubOps/pull/168#issuecomment-7189560351).
Real consent/fetch/calendar-write acceptance and backup restoration remain open.

The [grading guide](GRADING_GUIDE.md) maps the seven suggested rubric weights to
existing files and reproducible checks. The requirements' page 5 rewards the
demonstrated capability and impact of professional practices; it gives examples,
not a required tool list or fixed number of weekly meetings. Our C-31 team task
still needs team review of the board evidence. Four Monday dates are owner-reported;
commit summaries do not establish attendance or oral decisions. The native board
receipt is [native-fields-2026-11-23.json](board/evidence/native-fields-2026-11-23.json).

Current PR-head checks and individual review records, not old green runs or a
temporary waiver, establish delivery evidence. The OTLP/Jaeger proof remains
synthetic; producer hooks, deployed alerts and final held-out evaluation gates
remain open. No bonus score is predicted.

## Current scope update: 16 November 2026 (C-29)

The tables and runs below are dated history. Setup's service (#55) and application
wiring (#87) are merged. The new [actual-app setup regression](e2e/setup-live.spec.ts)
checks real HTTP cookies/SQLite on desktop and phone, without replacing routes:
skip/resume/completion, separate checklist state, missing-CSRF and adviser denial.
It uses synthetic clubs and no extraction, so it establishes local integration
rather than model quality, real Google login or ASME acceptance.

The optional OTLP exporter and synthetic Jaeger proof are implemented; see
[observability/README.md](observability/README.md). Real producer hooks and hosted
monitoring remain pending. The actual private
[task board](https://github.com/users/Nohra2005/projects/4/views/8) was populated and
verified under [#91](https://github.com/Nohra2005/ClubOps/pull/91); its tooling remains
in that separate PR. Three genuine team-review records are still needed. C-35's
inbox preview is separately reviewed in #94; it is not a live mailbox integration.

The [C-29 report draft](report/architecture-and-operations.md) links each architecture,
web/deployment and monitoring claim to its files and states remaining acceptance.
New local results are in [VERIFICATION.md](VERIFICATION.md#2026-11-16--c-29-actual-application-setup).
The baseline main `54d38c1` also has green [CI](https://github.com/Nohra2005/ClubOps/actions/runs/43752096664),
[Web](https://github.com/Nohra2005/ClubOps/actions/runs/43752096760) and
[Container](https://github.com/Nohra2005/ClubOps/actions/runs/43752096713) runs;
these establish that revision's checks, not the new C-29 PR head's result.
No workflow or backend implementation changed in C-29. Independent review, current
PR-head CI and the team's merge-freeze decision still govern publication to main.

## Historical baseline: 1 November 2026

Updated 1 November 2026. The course's **Bonus Engineering Practices** section (page 5)
rewards demonstrated capability and impact; **Final Demo Expectation** (page 6) asks for
failure/invalid/security cases. This table records evidence, not a predicted grade. Paths are repository-relative; npm commands run from `web/`.

| Practice                               | Implemented evidence and reproduction                                                                                                                              | Current limit                                                                                                                           |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| Reviewed delivery                      | [PR #44](https://github.com/Nohra2005/ClubOps/pull/44), small task-named commits; merge-commit requested                                                           | A different teammate must review; no self-approval or squash. Main protection remains T-40 work                                         |
| Frontend CI and code quality           | `.github/workflows/web.yml`: pinned actions, lockfiles, lint, format, units, strict types/build; `cd web && npm run check`                                         | PR checks are evidenced; main completion waits for review/merge                                                                         |
| Browser/API regression gates           | Demo accessibility, HTTP failures/limits, instruction warnings, real API cookies and human approval: `npm run test:e2e`, `test:e2e:http`, `test:e2e:live`          | Scripted/synthetic data; not provider-quality or real OAuth evidence                                                                    |
| Reproducible local deployment          | `docker-compose.yml`, separate production/local targets; `docker compose up --build`; `npm run test:e2e:compose`                                                   | Real hosting, OAuth client, provider configuration and recovery remain open                                                             |
| Actual persistence and auth checks     | `web/scripts/check-compose-persistence.mjs` replaces a local container and checks both SQLite and the old session; container workflow tests production auth guards | Local named volume; not a backup/restore or production-recovery claim                                                                   |
| Build input protection                 | `web/scripts/check-build-context.mjs` exports BuildKit's context and tests synthetic canaries; optional CA bundle uses a temporary secret                          | Does not replace J-16 secret/dependency scanning                                                                                        |
| Agent evaluation gates                 | Existing planning runner/protocol; C-22 owns final CI thresholds                                                                                                   | T-26 results/thresholds and private recordings are not yet available; ordinary scripted unit tests are not a measured evaluation result |
| Observability and controlled evolution | Existing scoped cost/run reporter retains outcomes and versions; C-25/C-26 own OTel and deployed dashboards/alerts                                                 | No OTel export, deployed monitoring, provider comparison or live token/latency values claimed by this PR                                |
| Team workflow and security             | [Coordination #43](https://github.com/Nohra2005/ClubOps/issues/43), explicit ownership and review instructions; J-13/J-16 owned by Joey                            | No Projects board, three completed sprints, enabled branch protection or measured defence-off/on security rate invented                 |

## Verified GitHub runs

- [Frontend quality and browser/API checks](https://github.com/Nohra2005/ClubOps/actions/runs/41332905874): both jobs passed, including the actual BuildKit context check.
- [Container/persistence and production auth guard](https://github.com/Nohra2005/ClubOps/actions/runs/41333987152): passed with a clean Linux build.
- [Python quality/coverage and dependency audit](https://github.com/Nohra2005/ClubOps/actions/runs/41333987085): passed.

These runs are tied to their commits, not a promise that every future head is green.
Current results and conditions are in `VERIFICATION.md`; the PR's Checks tab is the
authority for its latest head. The deployed/pilot/evaluation tasks stay open until their
own completion evidence exists.

**2 November follow-up:** PR #44 is merged with its 17 original commits preserved;
Web, Container and Python workflows are green on main `d5dfb17`. GitHub's PR #44 review
list has no review records, so independent-review evidence remains a T-40 process gap,
not something this document claims happened retroactively.

Tatiana fixed [issue #45](https://github.com/Nohra2005/ClubOps/issues/45) in PR #47
with a shared-connection lock and concurrency regression (F-131). The same local
Caddy/API suite now passes all 4 cases with no ASGI/SQLite errors in its captured log.
Public deployment/Google verification remains open.

[PR #54](https://github.com/Nohra2005/ClubOps/pull/54) adds C-27's isolated learning
evaluation and full synthetic record/replay regression. The command and limits are in
[LEARNING_EVALUATION.md](LEARNING_EVALUATION.md). This runs in root CI without keys;
it is not T-26's real private-set results or C-22's final held-out thresholds.

## Instructions for teammate agents

Read current main, your handoff, TASKS.md and contracts. Name your task; keep coherent
small commits; request another teammate's review; use a merge commit. Check shared
decision/failure IDs against main and open PRs. Run only synthetic/replay checks in CI.
Record an actual command, result, run/review link and limitation. Tell your user what you
started and what remains; do not call a tool installation proof of use. Reply in #43
to coordinate overlapping workflow/API/telemetry work. Assistants in separate sessions
cannot be directly messaged through this session's agent tools.

## 3 November 2026 — setup and board evidence (PR #55)

- C-21: owned service/router, explicit untrusted source/approval boundary, durable
  progress and extraction outbox; 18 cases including real authenticated SQLite
  Review storage. The test adapter is explicit; production registration remains with
  Tatiana. No actual ASME facts were supplied or invented.
- C-31: exact-commit TASKS.md plan, private Projects adapter and proposed weekly
  iterations. Twelve stateful/offline tests cover pagination, retries, identity
  conflicts, unsafe targets and preserved iteration IDs. They run in the existing
  web quality job through `npm run check`, with no token or remote writes.
- Local evidence: 439 Python tests, 92.99% coverage; full root static/schema/task gates;
  42 frontend units; four setup demo and six HTTP browser cases across desktop/phone.
  Reproducible commands and limits are in `VERIFICATION.md`, `CLUB_SETUP.md` and
  `PROJECT_BOARD.md`. Current-head check links and small commits are on PR #55.
- F-151 reproduces the answer-only stale-tab limit; a passing reproduction is not a safety guarantee. Its owner-approved question-token fix remains pending.
- Process evidence still missing: Projects scope/publication/team access, three real
  weekly reviews, and independent review of this PR. Tentative iterations are not
  attendance or completion evidence. Record only actual reviews under T-28.

The older #45 warning above is superseded by #47 and the four clean Caddy/API cases
recorded on 2 November in PR #54. That separate PR also records C-23/C-24 merged/main
verification and remains open for review; its source changes are not bundled here.

## 9 November 2026 — ready setup integration and existing board (PR #55)

Tatiana's #43 feedback is now reflected in the owned setup/board docs. Returned
source failures cannot advance setup or queue partial facts (F-174); the one-tab
limit remains explicit and accepted by the API owner (F-151/D-102). Validation:
20 setup cases; 530 Python tests passed, 1 skipped, 92.73% coverage and root gates;
42 frontend units, 12 board-tool tests and production build. These totals exclude
independent #54, whose five checks are green on c33be79.

The board plan targets Tatiana's reported existing ClubOps project with Wednesday
weeks from 4 November; current-main dry run pins 85 tasks at 4b3f17e. No Projects
scope means no live read-back/sync claim. Manual board content must be inspected
and safely reconciled before the importer can claim verified. Three actual reviews
still need evidence; planned dates and owner reports are not invented attendance.

**9 November final onboarding copy check:** setup now states to use one tab and that no chat history is required (D-103). Repeated frontend check passes (42 units, 12 board-tool tests, lint/format/types/build), and all four existing desktop/phone setup browser flows pass. Projects scope is now enabled, but full discovery returns no visible existing board; direct board URL/access is still required.

## 3 November 2026 — human review correction (C-27, PR #54)

At Tatiana's request, `export` now produces the requested seven-column private review
CSV with actual saved facts/answers and two blank ratings. `score` reads completed
yes/partly/no labels offline; no wording comparator or model assigns semantic grades.
Partly stays separate. The exact-word path is an explicit technical `smoke` only.
D-87 supersedes D-83's quality use, not planning's separate automatic evaluation.

File-backed checks: 48 evaluator regressions, 469 full Python tests / 92.93% coverage,
strict source/CLI typing and root gates; 40 frontend units and production build. The
actual synthetic replay exported two blank-rated rows with no key/network. Synthetic
ratings in tests prove mechanics only; Tatiana's real ten-case grades remain pending.
Commands, privacy, CSV import and limits are in `LEARNING_EVALUATION.md`; latest GitHub
checks and review evidence are on PR #54. No private sheet or source row is committed.

## 9 November 2026 — C-27 reviewer blockers addressed

Tatiana's #54 review identified actual frozen-file incompatibilities. Boundary fixes
allow source/expected `fact` sharing and translate the three documented source labels
without editing the frozen CSV or contracts. D-101/F-172/F-173 link those decisions
to regressions. All 70 evaluator tests pass, including record/replay of her headers
using synthetic evidence and a forbidden network during replay. Current main's learner
prompt required an explicit synthetic cassette refresh; no live provider was called.
Full root gates pass: 580 passed, 1 skipped, 92.69% coverage; frontend gates/40 units
also pass. See `LEARNING_EVALUATION.md` for the runnable private-header command.
Actual private grades and quality/cost measurements remain T-26, not these fixtures.

**After #54 merged on 9 November:** #55 now contains main 4bed33c and both task histories. Shared evidence/handoff conflicts preserve all entries. Combined root gates pass: 600 passed, 1 skipped, 92.68% coverage; Ruff/format (138 files), strict package types (76 files), CLI typing, schema/task checks. Frontend check passes with 42 units and 12 board-tool tests. Remote checks for the new merge head are on #55; previous 3e0180a had all five green. No production setup wiring or real private evaluation is implied.

## 10 November 2026 - C-33 explicit starter onboarding

C-33 implements the existing cabinet/document API workflow without inventing a
purpose-specific progress contract. Browser-local, identity-scoped ticks hold only
booleans; accepted uploads remain separate from learned/approved facts. Selection
makes no request, duplicate clicks are locked and failed/malformed responses preserve
retry state. D-105/F-179-F-182 link these boundaries to synthetic regressions.

Verification: all root gates, 600 passed / 1 skipped / 92.68% coverage; 48 frontend
units, 12 board-tool tests/build; 6 HTTP and 6 demo/setup browser cases, including
completed-checklist accessibility and phone overflow. A parallel artifact-folder
collision was resolved by a clean standalone rerun, not by disabling a check.
No real onboarding, deployed completion, consent or paid provider result is claimed.
C-33 stays doing until C-21 wiring and actual deployed verification. See
STARTER_CHECKLIST.md and the PR for commands, limits and independent review.

## 10 November 2026 - C-34 source and sharing review

C-34 makes the existing T-41 shared scope visible and president-controlled. Code
checks scope independently of card type; individual scope choices are sent only on
confirmation. All disagreements precede ordinary source groups, both comparison
quotes are shown, and failed requests preserve drafts. Bulk approval never silently
applies an unsaved sharing choice. D-104/F-175-F-178 link this to frontend regressions.

Verified: 600 Python tests passed, 1 skipped / 92.68% coverage and all root gates;
46 frontend units, 12 tool tests/build; 8 HTTP + 2 demo review browser cases and
2 accessibility cases across all 11 routes on desktop/phone. No live provider,
private data or backend-contract edit. `REVIEW_GUIDE.md` explains shared versus
club knowledge in two opening sentences and records the authorization limits.
Independent review/merge-commit evidence and final-head CI belong to the PR.
