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
