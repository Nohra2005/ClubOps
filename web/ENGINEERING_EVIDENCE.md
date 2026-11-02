# Engineering bonus: evidence and remaining work

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

**Open integration finding:** [issue #45](https://github.com/Nohra2005/ClubOps/issues/45)
records a reproduced intermittent SQLite member-lookup exception in the local real-API
Caddy path. A run with four passing assertions still emitted server exceptions, and a
focused repeat failed. This is referred to the API owner; green Linux/unit/container
checks are not being used to claim that the backend finding is fixed.

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
