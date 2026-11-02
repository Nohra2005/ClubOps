# Handoff log — Web app

Owner: Christophe El Chabab. Tasks in `TASKS.md`; protocol in `AGENTS.md`. See `docs/handoff/TEMPLATE.md` for the entry format. Append new entries at the bottom.

No entries yet.

## 2026-10-22 — Christophe, with Codex (feat/christophe-web-app)

**Did:** Built C-01 through C-12 from Tatiana's 14-page UI PDF: responsive React/TypeScript app, isolated persistent demo API plus guarded HTTP transport, all seven main screens, event planning/approval, Google sign-in entry, ASME setup and failure states. Google was explicitly chosen by Christophe; real OAuth still needs the backend. Work is split across small commits by feature and correction.

**State:** Frontend checks pass: 13 unit tests, 36 desktop/375px browser tests including accessibility, lint, formatting, types and production build. Existing 116 Python tests and root checks pass (UTF-8 mode for the Windows schema script). `web/VERIFICATION.md` records commands and limits. This entry is committed with the handoff; a draft PR is prepared next. Shared backend modules/contracts were not changed.

**Next:** C-13: agree the response models and missing action/auth endpoints in `web/API_NOTES.md` with Tatiana after T-22, then switch `VITE_API_MODE` from demo to http and test against the real API. C-14 waits for T-25 and C-13.

**Open questions / blockers:** Run detail-confirmation representation, revision-bound approval, action endpoints absent from the PDF, Google session/logout and calendar metadata, production chat history, shared-host SPA routing. Root CI still needs a frontend job from its owner. Synthetic fixtures and mock role switching are never production authentication or verified AUB policy.

## 2026-10-22 — Christophe, with Codex (C-16, PR #9)

**Did:** After the initial 22 frontend commits were published in [draft PR #9](https://github.com/Nohra2005/ClubOps/pull/9), Christophe explicitly authorized fixing its failed dependency audit, including the cross-area lockfile change. Commit `1043c2f` updates only `certifi` from 2026.7.22 to 2026.10.19 with uv, resolving PYSEC-2026-4320. Backend source, contracts and workflow definitions are unchanged. The PR targets `main` and has no merge conflicts.

**State:** The exact repaired lockfile installs successfully. Local pip-audit reports no known vulnerabilities; 116 Python tests pass with 93.63% coverage, and Ruff, mypy, schema and task checks pass. Windows tests use a fresh workspace temporary directory, and local audit tools use system certificate trust while retaining TLS verification. Both GitHub jobs (dependency audit and lint/types/tests/contracts) passed in [run 39793167497](https://github.com/Nohra2005/ClubOps/actions/runs/39793167497). C-16 is done; this follow-up documentation commit records the verified result. The PR remains a draft awaiting teammate review.

**Next:** Continue C-13 when T-22 is ready, using `web/API_NOTES.md` to agree the missing API and Google session contracts with Tatiana.

**Open questions / blockers:** The existing shared workflow runs Python checks and the dependency audit; frontend verification is recorded in `web/VERIFICATION.md` and is not yet a shared CI job. C-13 and deployment remain blocked as previously recorded.

## 2026-10-23 — Christophe, with Codex (C-17, PR #9)

**Did:** Merged main through `597685d` into the frontend branch in `4934469`, preserving backend work and all frontend commits. Resolved append conflicts by retaining main's published IDs and assigning D-55–D-59 / F-61–F-70 to our previously unpublished entries. Checked the 0.2.0 contracts and schemas, then added response adapters for run states/costs/questions, answer citation IDs/nullable fields, draft bodies/types/provenance and Result failure envelopes. Calendar handles nullable times/member ownership and hides cancelled items. Backend source, schemas, contracts and CI definitions were not edited by this task.

**State:** C-17 is in review in existing draft PR #9; this entry accompanies the final handoff commit before the branch update is pushed. Frontend checks pass with 33 unit tests. All 36 demo browser cases were verified (34 initial passes plus two chat rechecks after a duplicate-text fix); 8 isolated HTTP browser cases pass on desktop and 375px phones. Merged Python checks pass: 233 tests, 95.18% coverage, Ruff, mypy, schema and task validation. Implementation, browser coverage and handoff are separate commits. `web/VERIFICATION.md` records reproduction and the Windows test-server cleanup limitation.

**Next:** Verify PR #9's updated remote checks, then have Tatiana review the compatibility matrix in `web/API_NOTES.md` for T-22. C-13 stays blocked until the real HTTP/session endpoints exist; C-14 and C-15 retain their dependencies.

**Open questions / blockers:** Structured detail confirmation; HTTP event/review/knowledge/directory envelopes; draft URL type aliases and nested draft responses; revision-bound approvals; continue/stop, logout and other missing action endpoints; ordinary-member access and Google identity-to-actor mapping. Capability contracts do not provide every HTTP screen field. The shared workflow still has no frontend job; no model or Google calls were made by these tests.

## 2026-10-26 — Christophe, with Codex (C-13, direct-main work)

**Did:** Read the now-published `docs/api.md` and started C-13. Every changing HTTP request now includes the CSRF header, including uploads and bodiless rebuild/continue requests. The browser still sets multipart boundaries. Marked the merged C-17 complete.

**State:** Work proceeds in small commits directly on main at Christophe's explicit instruction, overriding the earlier PR/squash workflow for this work. Each completed portion is verified and pushed separately. After the first three commits, verify that GitHub main lists all three individually before continuing.

**Next:** Connect the published continue, sign-in/logout and bare UI response conventions; then C-19, C-20 and deployment preparation. Account configuration for Google and hosting is not known yet; do not claim external deployment or sign-in verification.

**Open questions / blockers:** T-22 part 1 documents working endpoints and explicit 501 placeholders; integration cannot make unfinished backend capabilities work. Persistent hosting and the public Google OAuth client ID still need setup.

## 2026-10-26 — Christophe, with Codex (C-13, C-18, C-19, C-20 on main)

**Did:** Connected CSRF, canonical runs and same-ID continuation, bare chat views, Google GIS credential exchange and guarded server logout. C-19 now serves deterministic, club-isolated role guides with all current citations and explicit gaps. C-20 records private-content-free run metadata, deduplicates costs/traces and exposes honest usage coverage plus a report CLI. Prepared Docker/Caddy same-origin packaging, a persistent Render Blueprint and account setup instructions. No frozen contracts changed. API changes are limited to the assigned handover/usage routes and their run-recording callbacks.

**State:** Each portion was committed and pushed separately directly to main at Christophe's explicit instruction; no new PR or squash. The required first-three checkpoint verified `9da7b68`, `550d28a`, `1139512` as separate GitHub main commits by `chrs-005` before continuing. Verification: 343 Python tests, 93.33% coverage, Ruff/mypy/schema/task gates; 38 frontend units; 36 demo, 18 intercepted HTTP, 2 real local-API and 4 production-router browser cases. Hosting schema, Caddy and Bash syntax validate. GitHub checks are green on hosting-preparation commit `8039a9b`; an intermediate evidence-classification failure was corrected separately in `f011231`. This entry accompanies the final verification commit. Runtime output and tools under `output/` remain untracked. Port 5173 still serves the demo.

**Next:** Configure the public Google OAuth web client and settle a hosting account/budget, then build the container and verify real sign-in, planning and persisted records on the deployed URL using `web/DEPLOYMENT.md`. C-19 is done. C-13/C-18 remain doing; C-14/C-15 retain their dependencies. C-20 implementation is ready but its real-provider pilot report/measurements remain pending, so its status is doing.

**Open questions / blockers:** Christophe does not know whether OAuth or Render resources exist. Render Free cannot attach a persistent disk; the prepared paid option has not been provisioned or charged. Docker's engine is stopped, so image construction is unverified. T-17/T-18/T-20/J-07 and uncontracted demo actions remain explicit API placeholders. For Tatiana: existing planning callbacks now write club-scoped run metadata; other feature producers must pass their known club context to `clubops.reports.traces.record_trace` before token/latency/retry metrics can appear. The global trace file is deliberately not read because its records lack club ownership. See `web/API_NOTES.md` for the precise integration boundary and `web/VERIFICATION.md` for reproducible evidence and limits.

## 2026-11-01 — Christophe, with Codex (PR #44: C-23, C-24, C-13, C-18, C-29)

**Did:** Pulled `d1a6a86`, read the requirements' bonus/demo pages and current task reassignment. Added separate frontend and container workflows, pinned actions and synthetic regression gates. Connected T-18 warning/outdated fields, restricted batch approval, aligned document formats/size and handled empty teaching review IDs. Docker context checks now exclude private/host artifacts; optional CA trust is a temporary secret. Built local/production images; Compose starts the full app with local-only synthetic sign-in and persistent data/session key. Updated assigned architecture, provenance, memory and setup docs without claiming automatic purge/monitoring. Task-named portions are separate commits.

**State:** Work uses the updated bonus PR/review/merge-commit protocol, not direct main pushes. PR #44 contains the work; #43 notifies Tatiana/Joey and asks their agents to tell their users and follow the evidence checklist. C-23/C-24 are review, C-13/C-18/C-29 remain doing. Verified: 388 Python tests, 92.77% coverage, root gates; 40 frontend units; 36 demo + 20 HTTP + 4 live/local-login + 4 actual Compose browser cases. Container replacement preserves the old session and synthetic record. Real Linux web/container CI has passed; see `web/ENGINEERING_EVIDENCE.md` and latest PR checks. No new contracts or teammate implementation folders changed.

**Next:** Tatiana reviews PR #44 and triages API issue #45; merge with a merge commit to preserve individual commits. Add successful new checks to T-40 branch protection when it becomes available. Joey should try the README-only fresh Compose setup and report the outcome for C-29. Ready subsequent Christophe tasks include C-21 setup and C-27 learning evaluation; C-22 needs T-26 thresholds and C-25/C-26 still need scoped real metadata/configuration.

**Open questions / blockers:** Local production-Caddy flow intermittently raises SQLite InterfaceError in session member lookup; a focused repeat failed despite an earlier four-assertion pass. #45 contains the synthetic reproduction; do not claim C-13 clean or change backend ownership without approval. Real Google client ID, provider and hosting/budget are still unknown. No public deployment, monitored service, evaluation result, completed sprint or enabled branch protection was invented. Runtime tools/logs stay untracked in `output/`. The isolated real local app remains at `http://127.0.0.1:18080/login`, synthetic `president@example.com`; no real data or paid model calls were used.

## 2026-11-03 — Christophe, with Codex (PR #55: C-21/C-31)

**Did:** Fetched main `d5dfb17`; PR #54 remains open/unreviewed, so this branch is independent. Built the owned setup service/router, durable per-club progress, Untrusted question sources and an outbox that retries exact Review proposals without another extraction. The screen validates responses, preserves failed drafts, resumes and distinguishes shared rules from demo examples. Built the TASKS-fed private Projects plan/create/sync CLI, four proposed weekly iterations, paginated reconciliation and read-back verification. Tool regressions now run in web CI. D-85/D-86 and F-138–F-150 record decisions/failures; each portion has a separate commit.

**State:** PR #55 is draft for owner integration; C-21 stays doing and C-31 is blocked on Projects access. Final local root gates pass: 438 tests, 92.99% coverage, Ruff/mypy/schema/tasks. Frontend gates pass: 42 units, 12 tool tests, lint/format/types/build. Setup has 17 service/router/actual-auth/SQLite tests, four demo browser cases and six intercepted HTTP cases across desktop/phone. The default board dry run reads 77 main tasks. Current-head CI is tracked on the PR. No frozen contract or teammate implementation changed; no real data or paid model call was introduced. The lower total than #54 is because this branch excludes its 20 evaluator tests.

**Next:** Tatiana wires the setup router/public callbacks and `/me.club.setup_complete`, reviews idempotent submission including prior Review decisions, and supplies sourced non-personal ASME seed facts. `web/CLUB_SETUP.md` specifies the boundary and test adapter. Christophe enables Projects through `gh auth refresh -s project`; then publish with the documented CLI, verify read-back/team access and agree real weekly ten-minute reviews. Record three actual reviews under T-28 before calling C-31 done. Review #54/#55 independently and merge with merge commits; preserve additive log entries if both PRs touch them.

**Open questions / blockers:** The CLI token lacks even read:project and the browser host is unavailable; no live board or teammate access has been verified. Planned weeks are not completed reviews. The original answer-only setup contract cannot protect against every stale-tab/delayed retry; the requested question-token extension needs the API owner. Main still serves the 501 setup placeholder until owner wiring. Real ASME seed facts, OAuth/provider/hosting configuration and actual evaluation remain pending. The older #45 finding was fixed by #47 and rechecked clean in the separate #54 work. `output/` stays untracked; older CONTRIBUTING squash wording needs owner reconciliation with current AGENTS merge-commit instructions.
