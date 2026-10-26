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
