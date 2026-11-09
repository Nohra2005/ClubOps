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

## 9 November 2026 ? C-27 reviewer blockers addressed

Tatiana's #54 review identified actual frozen-file incompatibilities. Boundary fixes
allow source/expected `fact` sharing and translate the three documented source labels
without editing the frozen CSV or contracts. D-101/F-172/F-173 link those decisions
to regressions. All 70 evaluator tests pass, including record/replay of her headers
using synthetic evidence and a forbidden network during replay. Current main's learner
prompt required an explicit synthetic cassette refresh; no live provider was called.
Full root gates pass: 580 passed, 1 skipped, 92.69% coverage; frontend gates/40 units
also pass. See `LEARNING_EVALUATION.md` for the runnable private-header command.
Actual private grades and quality/cost measurements remain T-26, not these fixtures.
