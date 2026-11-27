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

**Additional pre-review check (3 November):** F-151 now has an explicit stale-tab reproduction, not a safety-pass claim. Final totals are 439 Python tests / 92.99% coverage and 18 setup cases, with the same frontend/tool/browser results above. The task remains incomplete pending the owner-approved question-token decision. PR #55 contains 20 focused commits after the final evidence update; no production wiring or board publication was claimed.


## 2026-11-09 — Christophe, with Codex (PR #55: ready for API integration)

**Did:** Synced independent #55 with main `4b3f17e`, preserving additive logs. Read Tatiana's #43 reply: she will wire setup after draft removal, accepts the one-tab limit without a question-token extension, owns ASME seeding in T-09, and reports an existing ClubOps board with Christophe admin / Wednesday reviews from 4 November. Recorded that decision instead of extending contracts. Current CaptureResult.sources_failed now keeps setup retryable before any partial queue writes (F-174). Integration tests derive shared-rule counts from the sourced rulebook (now 27). C-31's local plan targets the existing Nohra2005/ClubOps board/cadence and explicitly requires inspection/adoption of manual content rather than creating a duplicate. C-29 architecture/memory/provenance docs reflect current published decisions and green main CI.

**State:** Ready for Tatiana's requested integration/review; C-21 remains doing, C-31 blocked on scope/live inspection and actual review evidence, C-29 doing. Root gates pass: 530 passed, 1 skipped, 92.73% coverage; Ruff/format (132 files), strict types (75 files), schema/task checks. All 20 setup cases pass, frontend gates pass (42 units, 12 board-tool tests), and main dry run reads 85 tasks. D-102/F-174 are reserved beyond #54's D-101/F-172/F-173; F-151 remains an accepted limit, not a solved race. #54's learning fixes are separate and all five remote checks pass on c33be79.

**Next:** Make #55 ready as Tatiana requested and hand off app.py route plus /me completion wiring, bounded public capture and decided-card queue idempotence. API owner should verify actual setup/second-club retrieval after integration. After Christophe completes `gh auth refresh -s project`, inspect the existing board's real owner/number/privacy/fields/cards/iterations, adapt import safely if manual cards are unmarked, then verify sync read-back and teammate visibility. No new board should be created. Record only actual Wednesday review dates/outcomes under T-28.

**Open questions / blockers:** Latest Projects read still fails for missing scope; a user command omitted the required word project and was corrected. Existing-board/admin status is Tatiana's report, not verified API access here. The current sync refuses unmarked/manual/conflicting boards intentionally; do not overwrite their history to bypass this. Production setup is still 501 until Tatiana wires it. Private ASME facts, real OAuth/deployed validation and real learning ratings are not fabricated. `output/` stays untracked; no paid calls or teammate implementation edits.

**Same-day onboarding/access update:** Christophe relayed Tatiana's request to sync #55 and drop WhatsApp histories as onboarding. GitHub confirms #55 is MERGEABLE with main 4b3f17e contained, contracts 0.2.3, and no remaining shared-doc conflicts. Kept merge history rather than rewriting published small commits. C-21 is now the primary president-interview path; UI/guide explicitly say no chat history is required and use one tab (D-103). Tatiana will wire her API files after merge for ASME on Wednesday 11 November. Projects scope is now enabled, but complete GraphQL discovery of both users and repo-linked boards returns zero visible projects; the supplied repo link is not a board URL. Need Tatiana to supply direct project URL/access; no duplicate created. C-27 all five checks remain green.
## 2026-11-02 — Christophe, with Codex (PR #54: C-27 learning evaluation)

**Did:** Pulled main `d5dfb17`; confirmed PR #44's 17 commits are retained and its CI gates now pass on main. Rechecked Tatiana's #47 fix for #45: the same Caddy/API suite passes all 4 cases without server exceptions. C-23/C-24 marked done. Built the ready C-27 evaluator/CLI: private CSV mappings, exact labelled statements/aliases, scoped verified facts, wrong/missed/duplicate counts, new-fact citation reuse, operational errors and budget costs. Each case uses a new sandbox with deterministic IDs/date for replay. Labels never enter prompts; reports exclude source/answer text. Added actual synthetic recordings and an offline example, all split across small commits.

**State:** C-27 is review in PR #54. Root gates pass: 441 tests, 92.99% coverage, Ruff/mypy/schema/tasks; CLI also passes strict mypy. All 20 new evaluator tests pass, including actual record -> replay with network forbidden and no key. Frontend checks pass (40 units). The documented fixture CLI produces a metadata-only table (2 cases, 1 learned expected fact, 1 new citation, 0 errors). These are synthetic smoke results, not real quality/cost measurements. D-83/D-84 and F-132–F-137 record decisions/regressions; no frozen contracts or teammate implementation changed. Final CI and non-author review are checked on PR #54 before merge.

**Next:** Tatiana confirms the frozen learning CSV headers/canonical labels, reviews PR #54 and uses explicit column mappings without modifying frozen bytes. Run the private set with deliberate provider record mode in T-26; later set C-22 thresholds from measured results. Merge with a merge commit to preserve individual commits and leave real review evidence. C-21 setup and C-31 board remain ready next tasks; deployment/monitoring need configuration.

**Open questions / blockers:** Private schema details were requested in coordination issue #43 (column names only, no private rows); JSON/plain-label mappings allow independent synthetic completion. Exact wording/aliases and citation reuse are deliberately limited metrics, not semantic accuracy or human acceptance. The benchmark auto-verifies only in fresh evaluator memory and measures create cases, not cumulative merge or shared-policy approval. Real OAuth/provider/hosting configuration and T-26 results remain unknown/pending. No paid calls, real data, deployment or evaluation-quality claims were introduced; `output/` remains untracked. #44 has no GitHub review records in the checked metadata, so T-40's review-evidence practice still needs attention despite its merge.

## 2026-11-03 — Christophe, with Codex (PR #54: Tatiana's C-27 review revision)

**Did:** Adopted Tatiana's feedback as relayed by Christophe: export a private CSV with id, expected fact, actual saved fact(s), question, actual answer, blank learned and blank answer_ok. A second offline command validates yes/partly/no labels and builds the results table. Partly has no invented numeric weight. Exact-word/citation checks are now an explicit technical smoke mode, not semantic quality scoring. Original IDs and frozen input bytes are preserved; private evidence stays in the sheet, while the companion/results hold hashes and operational/cost metadata. Added formula-safe literal CSV export, new-file/input guards and complete-row validation. Changes are separate commits on #54, independent of #55.

**State:** C-27 is review again. Root gates pass on main `22c4dae` plus this branch: 469 tests, 92.93% coverage, Ruff/mypy/schema/tasks and explicit CLI typing. All 48 C-27 tests pass, including actual public-pipeline record/replay and score with model/configuration access forbidden. Frontend checks pass (40 units). The real synthetic replay command exported two cases, no errors and blank ratings; no actual human-study result was created. Linux CI found a temp-path assumption in the output-boundary test; it was fixed with an explicit test repo root. D-87 and F-152–F-159 reserve the new decisions/failures beyond #55's ranges.

**Next:** Tatiana reviews #54, maps her frozen private headers without rewriting the CSV, exports each run to an ignored private location, fills only the final two columns and runs `score` with the matching companion. See `web/LEARNING_EVALUATION.md` for exact commands and rating meanings. Planning T-05/C-32 are not reinstated; the ten learning tests are the scoped human-review exception. T-26 supplies real measurements and later C-22 thresholds. Merge only after independent review, green checks and a merge commit preserving the small commits.

**Open questions / blockers:** No real private learning CSV/ratings were supplied or examined. A reviewer must complete both ratings on every row; results cannot be fabricated from blank cells. Companion hashes detect changed evidence/missing rows, not malicious modification of both files or authenticated reviewer identity. Preserve the matching run files and input date/model for replay. Original exact-label guidance in the 2 November entry is superseded for quality by D-87 and the new guide. #55 remains separate for setup/Projects; its owner/access dependencies were not bypassed while prioritizing this fix. `output/` remains untracked.


## 2026-11-09 — Christophe, with Codex (PR #54: frozen learning CSV review fixes)

**Did:** Read Tatiana's 4 November changes-requested review. C-27 now allows the same fact column for source and expected text while retaining a separate question. CSV-only aliases map chat -> chat_message, after_event_form -> form and forwarded_email -> email, leaving contracts unchanged. Added frozen-header record/replay tests for all three labels and sanitized unknown-label tests. Synced main `4b3f17e`, preserving both teams' additive logs; refreshed three synthetic recordings through MockTransport for D-95/current prompts. These are separate commits, not a squash.

**State:** C-27 remains review on #54. All 70 C-27 tests pass; full root verification passes with 580 passed, 1 skipped and 92.69% coverage, Ruff/format, strict package/CLI typing and schema/task checks. Frontend check passes with 40 units and production build. D-101/F-172/F-173 record the mapping choices/regressions. No private file, actual reviewer rating, paid call or teammate implementation was used. Current-head CI and Tatiana's re-review are required before merge.

**Next:** Tatiana can use the exact frozen-header command in `web/LEARNING_EVALUATION.md`, complete both human ratings, then run offline score. Do not rewrite her frozen CSV. Keep the sheet/companion private and together. Re-review #54 and merge with a merge commit when green/approved. Next return to #55: Tatiana's #43 response requests making it ready so she can wire C-21, declines question-token extension, and says the existing ClubOps board has Wednesday reviews from 4 November.

**Open questions / blockers:** The private ten-case run/ratings remain Tatiana's work. GitHub CLI still lacks Projects access, so no live board read/sync or completed sprint evidence is claimed. #55 integration/access remains separate; the documented two-tab setup limit is accepted by the API owner, not fixed by changing contracts. `output/` stays untracked.


## 2026-11-09 - Christophe, with Codex (PR #55: sync after #54 landed)

**Did:** #54 merged as main 4bed33c while the previous #55 head's fifth check was completing. Merged new main immediately, resolving fresh additive conflicts in design/failure logs, web handoff and verification/evidence; retained all C-27 and C-21 entries. No application code conflict or contract change. Marked the merged C-27 runner done; actual private ratings remain T-26.

**State:** Combined root gates pass: 600 passed, 1 skipped, 92.68% coverage; Ruff/format (138 files), strict package types (76 files), explicit CLI typing, schema/task checks. Frontend check passes with 42 units, 12 board-tool tests and build. The earlier head 3e0180a had all five remote checks green; new merged-head checks are tracked on #55. Both setup and learning regressions now run together. C-21 integration remains with Tatiana after merge; C-31 still needs direct board URL/access despite enabled Projects scope.

**Next:** Tatiana independently reviews and merges #55 with Create a merge commit, then wires setup route and /me for ASME on 11 November. Do not squash the remaining small setup commits. Keep the recorded primary-interview/no-chat onboarding decision, accepted one-tab limit and retry failure guard. No real-data or paid calls were introduced. Runtime output remains untracked.


## 2026-11-10 - Christophe, with Codex (C-28: script and disclosed synthetic rehearsal)

**Did:** Created the missing five-minute presenter script, strict synthetic HTTP screenplay and browser rehearsal. Six chapters cover context, a question/normal plan/explicit approval, a run limit, an uploaded instruction warning and rejection, a read-only adviser plus scripted 403, then honest evidence/limits. All API traffic is intercepted; unregistered actions and external requests fail closed, including the bare /api prefix. Disclosure is persistent, and no application src, backend implementation, shared contract or provider was changed. The fast desktop/phone check is in existing HTTP CI; fixture tests and strict runner typing are in web check. Added a recording launcher with a checked, freshly allocated workspace directory passed to every worker.

**State:** C-28 remains doing because C-14/C-18, observed real backend/model/security outcomes, team rehearsal and final narrated footage remain pending. Actual corrected-launcher silent recording completed: 301.56 seconds, 28,294,899 bytes, SHA-256 edc6e8dde7abdfd0fe1f25ef2d300422ff17549b3a9ed89e40f1dbd2310b748b. Six chapters passed, one of each declared action, zero unexpected requests; five extracted frames were visually inspected. Public summary and two disclosed frames are in web/demo/evidence; raw movie/proof remain in output/demo-rehearsal-vxalCU. Recorded runner revision e47db05 is stated; the later bare-prefix guard leaves scene footage unchanged. The first take exposed per-worker config paths; the launcher fixes that, and a fresh full take verifies one printed output directory. Missing FFmpeg/certificate-chain setup was resolved with Playwright's encoder and Node's system certificate store, preserving TLS verification.

**Validation:** Independent from #75/#76/#77, based on main 106baa7. Root make-check equivalents pass: 600 passed, 1 skipped, 92.68% coverage, Ruff/format, strict mypy, schema/task checks; final shared-doc/task regressions also pass (8). Final web check passes with 57 units (15 new screenplay/target cases), 12 board-tool cases, strict rehearsal/app types and production build. Full HTTP suite passes 30 cases; the four rehearsal/egress cases were rerun after the bare-prefix correction. Recording config --list and an actual five-minute take both pass. D-107/F-192 to F-196 are beyond all main/open-PR ranges. Current-head remote CI and independent review are still required before merge; preserve commits.

**Next / limits:** Tatiana and Joey review the timed script and supply real backend defense/permission outcomes and approved synthetic account setup for the final deployed run. Rehearse once with the team, add narration, save/hash the final backup, and record actual acceptance in the evidence ledger. Do not present supplied warning/403 fixtures as detection or authorization measurements, quote zero fixture cost as provider billing, or call this a real ASME onboarding. No real/private inputs, paid calls, messages outside authorized GitHub coordination, public deployment or completed-grade claim. Other PRs remain separate; use a substantive non-author review and Create a merge commit. output remains untracked.
## 2026-11-10 - Christophe, with Codex (C-25: optional OTLP export and local viewer)

**Did:** Built the optional closed-run OTLP/HTTP JSON exporter under reports, against contracts 0.2.3 only. Explicit producer club/run/step associations and aware windows are required; no joins are guessed from unrelated JSONL. Projection omits private fields/raw IDs and permits only exact trusted public labels. Default-off, one bounded HTTP attempt, typed failure/partial results, no ambient proxies/redirects, no raw collector diagnostics or unapproved dependencies. Added a separate pinned, loopback-only Jaeger demo and documented the exact producer boundary. Real Jaeger readback and an inspected browser image show a synthetic root, two steps and two model-call children. Its empty default acknowledgement led to a regression fix.

**State:** C-25 stays doing; actual agent/model hooks and finalized-run lifecycle remain with the owners, and C-20 provider validation is pending. Root gates pass: 664 passed, 1 skipped, 92.99% coverage, Ruff/format (147 files), strict types (80 files), schema/tasks. All 64 focused telemetry tests pass offline. Frontend check passes: 42 units, 12 board-tool tests and production build. Actual collector proof is in web/observability/evidence with a reproducible guide; all timings/counts there are synthetic, with zero tokens/cost and no provider. D-106/F-183 to F-190 are beyond main and open #75/#76's reserved ranges. Main 106baa7 was fetched/merged; independent reviews and current-head CI remain required.

**Next:** Tatiana reviews the exporter and wires real call-site context/timestamps, reviewed public technical labels, bounded async worker delivery and failure isolation. Do not use capability end-to-end timing as a model-call measurement. Submit a finalized run once, retaining its actual step/call windows; resume, durable queues and exactly-once delivery are not implemented here. Re-run a real producer integration test and viewer proof before marking C-25 done. Merge with Create a merge commit, preserving the small commits. #75 and #76 remain separate, green, unmerged PRs awaiting teammate review.

**Open questions / blockers:** No production app hook, hosted monitoring/dashboard/alert, provider billing proof, real ASME run or bonus-grade result is claimed. C-18/OAuth/hosting, C-20 real-provider validation, C-22 measured thresholds and C-31 existing-board URL/access remain pending. The local unauthenticated memory viewer is only for synthetic data and loses traces when stopped. Temporary readback/browser/runtime files remain untracked under output; no real/private inputs or paid calls were used. Owner coordination is in #43, with a request to relay this scope to users/agents.

**Contract review follow-up:** Removed an unsupported equality assumption between steps_used and the visible step list; the public contract does not require that relationship. Preserve both as supplied, with a regression and F-191. Full root gates reran green: 664 passed, 1 skipped, 92.99%; 64 telemetry cases remain. The prior PR head passed all five CI checks; the corrected fifteenth commit requires its own current-head checks.
## 2026-11-10 - Christophe, with Codex (C-33 starter checklist)

**Did:** Started independently from main 106baa7 while #75 remains open. After the explicit completed interview response, added cabinet check/settings action, club constitution/rules upload, past proposal upload and places/partners acknowledgement. File selection makes no request; each upload needs a click and valid document acknowledgement. Strict file/cabinet/response checks preserve pending state on failures. Local ticks whitelist booleans only and isolate mode/club/member; no raw files, filenames, member details or answers are kept there. Interview completion wording no longer claims the whole club is ready. Demo accepts the supported starter formats as unverified documents. No backend implementation/contracts or account/host settings changed.

**State:** C-33 stays doing because C-21 app wiring and deployed new-club verification remain open. Frontend check passes with 48 units, 12 board-tool tests and build. All root gates pass: 600 passed, 1 skipped, 92.68% coverage; Ruff/format (138 files), strict types (76 files), schemas/tasks. Focused browser checks: 6 HTTP starter cases and 6 demo/setup cases; the completed checklist is scanned for accessibility and horizontal overflow on desktop/375px phone. A local parallel Playwright run collided in their shared artifact folder; the demo suite was rerun alone and all 6 passed. Do not run default-output browser suites concurrently. D-105/F-179-F-182 reserve this change after #75's D-104/F-175-F-178; final fetch found no other open PR.

**Next:** Publish for independent review; use Create a merge commit. Tatiana wires C-21 route and /me, then verify the actual deployed interview/checklist/Review and ASME onboarding. Purpose-specific durable cross-device checklist progress would need a separate agreed contract; current UI does not infer it. Guide: web/STARTER_CHECKLIST.md. Preserve both #75 and C-33 task/log/handoff entries if merging both.

**Open questions / blockers:** No deployed URL/OAuth/provider setup or actual ASME source processing was introduced. C-21 remains the dependency; C-33 browser-local ticks are not server completion or approved knowledge. HTTP tests intercept synthetic responses; demo documents remain unverified and their facts pending Review. C-31 still needs direct board URL/access. Runtime output stays untracked; no real data or paid model calls.

## 2026-11-10 - Christophe, with Codex (C-34 Review sharing)

**Did:** Resumed from the interruption with only the task claim saved, pulled main 106baa7 and current locked dependencies, confirmed T-41 done and #55 merged with commit history preserved. Added shared-scope badges/president choices, explicit boolean decision payloads, quoted evidence for both comparison sides and missing-quote notices. All disagreements appear first; shared/disputed/warned/outdated cards and unsaved sharing choices never batch. Denied individual requests keep edits/choice for explicit retry. Demo follows the actual single-president T-41 path; legacy waiting responses remain display-compatible. Separate task/policy/UI/demo/browser/docs commits; no backend implementation/contracts changed.

**State:** C-34 review. All root gates pass: 600 passed, 1 skipped, 92.68% coverage, Ruff/format (138 files), strict types (76 files), schema/task checks. Frontend check passes: 46 units, 12 board-tool tests and production build. Focused browser checks: 8 HTTP review cases and 2 demo review cases; 2 accessibility cases scan all 11 main routes on desktop/phone. D-104/F-175-F-178 are the new ranges; they were free on main and no PR was open at final fetch. Frontend failure rows use the existing frontend-covered classification; the root validator's covered label is Python-only. No real sources, paid model calls, deployed or real-user acceptance claim.

**Next:** Publish C-34 for independent teammate review, then merge with Create a merge commit. Tatiana should add the existing shared fields to her docs/api.md and link the frontend evidence in docs/evidence.md/rubric-map.md. See web/REVIEW_GUIDE.md and web/API_NOTES.md for user guidance/API boundary. Current-head remote checks remain on the PR.

**Open questions / blockers:** C-21 production wiring remains Tatiana's app.py task; C-33 depends on it. C-31 still needs the direct board URL/access: project scope is enabled but the last discovery returned no boards. No duplicate project or attendance record invented. HTTP browser checks intercept synthetic responses; existing T-41 tests enforce server authorization, while frontend controls do not replace it. Runtime output stays untracked.


## 2026-11-11 - Christophe (C-31 exact board target and access audit)

Recorded the user-provided Nohra2005 project #4 URL in the owned guide/task. Current CLI viewer is chrs-005 and response scopes include project, but project view, field-list and item-list all fail to resolve #4. The error cannot prove whether the board is missing or private to another account. Asked Tatiana in #43 to verify target/access; no duplicate, permission/visibility change, marker adoption, card sync or review attendance invented. Gmail connector unavailable; browser app access timed out. C-31 stays blocked until actual read-back/inspection and eventual three weekly reviews. This is metadata/docs maintenance, with no new design/failure IDs or backend change.

Checks for this C-31 documentation update: root gates 603 passed, 1 skipped, 92.47%; web check 46 units, 12 board-tool tests and build; targeted task/failure docs 8 passed. No new test implementation is needed for the reversible URL/documentation change. Current-head CI and teammate review remain required.
## 2026-11-11 - Christophe (C-28 review revision)

Synced main afbdead and retained both shared logs. Removed all edits to Tatiana-owned evidence/rubric files; owned demo guides/proofs remain for her to link. Added primary president onboarding before planning: one explicit synthetic name answer pending Review, stop/resume with no resubmission, then reject the practice fact. Interview stays incomplete/paused; no chat history or personal data. Seven chapters still budget 300 seconds. D-117/F-202 follow #90's D-113-D-116 and other PRs through F-201.

Validation: root gates 603 passed, 1 skipped, 92.47%; web check 62 units + 12 tools/types/build; full HTTP 36 passed. Actual refreshed recording is 301.60 seconds, 29,148,641 bytes, SHA-256 db7c225ac858d4d4d9a1a94cdcfffeb1b382ea9dfb95b96702519421756c4abd. Seven chapters and onboarding counts (2 resumes, 1 answer, 1 rejection) verify; five frames inspected. New take/proof: output/demo-rehearsal-paE1hg; selected metadata/stills in web/demo/evidence. The 10 November six-chapter snapshot is explicitly historical. C-34 done; C-25/C-28/C-33 doing. Deployment, real backend/model/security outcomes, team rehearsal and final narration remain pending; current-head CI/re-review required.
## 2026-11-11 - Christophe (C-25 review sync)

Merged main afbdead into #77, preserving both teams' additive entries and original commits. Removed this PR's edits to docs/evidence.md and docs/rubric-map.md per Tatiana's ownership review; owned telemetry guide/proof remain available for her to link. C-34 is done; C-25/C-28/C-33 stay doing. No exporter, backend or contract implementation changed. Current-head checks and independent re-review are required.

Verification on the synced C-25 branch: full root gates pass with 667 passed, 1 skipped, 92.79% coverage; web check has 46 units + 12 tools/build. The evidence/rubric files have zero diff from main. Original 64 telemetry cases remain; real producer integration is still pending.
## 2026-11-11 - Christophe (C-33 review sync)

Merged main afbdead into #76 without squashing. Preserved all six distinct C-33/C-34 HTTP tests and both sides of additive logs/evidence. C-34 is done after #75 merged; C-25/C-28/C-33 stay doing while their PRs/acceptance remain open. Root gates: 603 passed, 1 skipped, 92.47%; web check 52 units + 12 tool tests/build; full HTTP 38 passed. Setup wiring from #87 is retained; deployed/real-club acceptance remains pending. No new shared IDs or backend implementation changed.

The starter guide and C-21 task now acknowledge #87's merged wiring; remaining C-33/C-21 acceptance is actual deployed/new-club verification, not the former 501 placeholder.

## 2026-11-12 - Christophe (C-31 access restored; manual board inspected)

**Did:** Synced #91 with main 2fff794 through a merge commit; resolved TASKS and handoff conflicts additively, retaining every merged C-25/C-28/C-33 update and the previous C-31 audit. Read project #4 as chrs-005: ClubOps, owner Nohra2005, private/open, 17 fields, three manual issue cards (#43/#83/#84), all Backlog. Recorded exact status options, existing Iteration field and absent management marker. Access is resolved; C-31 is doing. No fields/cards/permissions or visibility changed, no duplicate board, and no importer's marker stamped over manual history.

**Checks:** All root make-check equivalents pass: 667 passed, 1 skipped, 92.79%, Ruff/format, strict mypy, schema/task checks. Web check: 68 units, 12 board-tool cases, types/build. Read-only plan pins main 2fff794, reads 90 tasks and reports published:false at output/c31-current-main-plan.json. Documentation-only refresh adds no test implementation or shared IDs. CI/re-review still required on the pushed head.

**Next / limits:** Add an explicit additive adoption adapter that preserves the three issue cards, existing status/iteration identities and unrelated/manual content. Inspect actual iteration configuration before publishing sprint assignments. Existing normal --apply must keep refusing this incompatible unmanaged layout; do not change it to bypass inspection. Verify the full live sync afterward; three actual weekly reviews are still missing. #94 separately holds C-35's 11 small commits and D-124/F-214-F-218; do not lose either branch's additive task/handoff entries. Independent review plus Create a merge commit required. No private data or real club actions were introduced.

## 2026-11-12 - Christophe (C-31 additive import and actual board evidence)

**Did:** Continued #91 in output/c31-worktree so the main checkout and C-35 preview at port 5173 stay untouched. Added dedicated/additive field profiles, strict target/namespace/view/card preflight, explicit read-only --adopt preview, bound README append and normal resumable sync. Namespaced ClubOps status/owner/task id/needs/sprint fields avoid claiming the original Status/Iteration. Full read-back checks task fields and selected manual objects/README/visibility. No collaborators, visibility, existing card content or original field/view IDs were changed. Separate small commits preserve the reviewed-PR workflow.

**Actual live result:** Imported 90 task drafts from merged main 2fff794 into the existing private project #4; its three original cards remain (93 total, 22 fields). Initial larger mutation batches stopped after partial creations while quota was available; read-back recovered 29 existing tasks. Batches bounded at five completed the remaining 61 creations and 372 field updates. A repeat run verified created:0, updates:0 and unmanaged_preserved:true. Metadata-only proof is web/board/evidence/live-sync.json, including source/tool commits, actual status counts and limits. No raw manual body, credential or real club data goes into this proof. Board statuses intentionally mirror merged TASKS, not unmerged PR progress.

**Checks:** All root make-check equivalents passed: Ruff/format, mypy, schemas/tasks, 667 passed, 1 skipped, 92.79% coverage. Final shared docs/tasks checks: 10 passed. Web check: 68 units, 25 synthetic tool cases, strict app/rehearsal types and production build. Synthetic tests cover 123 tasks plus manual cards, unsafe/ambiguous target refusal before writes, namespace collisions, partial field/card recovery, no-op repeat sync, preservation/tampering and cyclic pagination. API schema inputs were inspected; the receipt never equates field verification with visual grouping. D-125/F-219-F-224 follow all main/open-PR reservations. Final-head CI and independent review remain required on the pushed PR.

**Next / remaining:** C-31 stays doing. View #7 ClubOps tasks by status exists as BOARD_LAYOUT, but groupByFields is empty. Supported create/update view configuration only accepts visibleFieldIds, not grouping. CUA was stopped because it could not verify the current Chrome URL; no UI workaround was attempted. User was asked to choose Group by -> ClubOps status and save; verify the result through the read-only groupByFields API when confirmed. Three actual weekly reviews still lack evidence; automatically completed past iteration dates do not prove meetings. Ask Tatiana to link this owned guide/proof from her evidence/rubric docs. Re-sync merged main after reviewed task PRs merge. Preserve both #94 and #91 additive handoffs/tasks, use independent review and Create a merge commit, no self-merge/direct-main push. C-35 HTTP shapes and J-16 ownership remain with the owners.

**Same-session column completion (supersedes the manual-step request above):** Official GitHub documentation distinguishes horizontal Group by from the board Column field. Supported GraphQL view input only edits visible fields, but the documented REST create-view endpoint accepts vertical_group_by. Added --columns to create a separate ClubOps status columns view (#8) through REST and verify GraphQL verticalGroupByFields. Original views, including #7, remain intact. Exact live link: https://github.com/users/Nohra2005/projects/4/views/8 . REST omits some unrelated GraphQL built-ins, so numeric mapping checks every required identity rather than total equality; pages are fully read. The completed command verifies the correct column field and preserves previous views; repeating it creates no cards, updates or view. Proof includes the separate column receipt and observation timestamp. No manual UI step remains. Christophe was told to ignore the earlier Group by request after he could not find it.

Final local web check passes with 68 units, 32 tool tests, lint/format, strict app/rehearsal types and build. Final shared docs checks: 10 passed. Root 667 passed/1 skipped/92.79% remains the relevant unchanged backend run. New F-225/F-226 cover horizontal-vs-vertical semantics and REST/GraphQL field projections; D-125 describes the final REST choice. Earlier all-green CI was for the previous head; current final-head checks are on #91. This batch retains 14 new small commits. C-31 remains doing solely for the three actual weekly review records and owner review/merge, not a claimed browser limitation. Please link the owned guide/proof in Tatiana-maintained evidence/rubric docs, use Create a merge commit and re-sync main after merged task changes. The running C-35 preview and original checkout were not changed.

## 2026-11-16 - Christophe (C-31 merged-task refresh)

**Did:** Fast-forwarded the existing board branch to Tatiana's main sync (8d31e2f). Refreshed private project #4 from merged main 54d38c1: 92 task drafts, 2 new cards, 99 field/body updates, verified with unmanaged cards preserved. Existing status-columns view #8 was reused. A second full sync verified 0 creates and 0 updates, no new view. Metadata-only proof is web/board/evidence/refresh-2026-11-16.json; the 12 November receipt remains historical.

**State / next:** C-31 stays doing; three actual team-review records remain absent. No code or contract changed. Shared-doc/task checks and proof formatting are rerun; previous head's five CI checks were green, new proof head needs its own CI/review. Follow the team's merge-freeze decision and preserve commits. Only merged TASKS statuses are imported, not this branch's or other PRs' unmerged progress.

**Open questions / blockers:** No participants/meeting outcomes invented; no public exposure, duplicate board, changed manual Status/Iteration, private club data, provider usage or main merge. Tatiana should link the dated proof from her evidence index. The 90-task count in earlier entries is the actual 12 November snapshot, superseded by this dated refresh.

## 2026-11-18 - Christophe (C-31 main sync and current task refresh)

**Did:** Resolved #91 main-sync conflicts additively, retaining the new Gmail/J-22 rows and the board evidence/history. Actual private project #4 now mirrors merged main 166f27e: 92 tasks, 0 new cards, 100 field/body updates. The same status-columns view #8 and manual objects are preserved. Repeat full sync verifies 0 creates/0 updates and no new view. Full metadata-only receipts: web/board/evidence/refresh-2026-11-18.json; earlier dated proofs remain history.

**State / next:** C-31 stays doing, because three genuine weekly team reviews still lack records. This batch changes no importer or contract behavior. Shared-doc/task checks and board-tool/front-end checks are rerun; current-head CI/review remains required. Main-based Python gates verified separately in C-35: 693 tests, 93.06% coverage and static/schema/task checks pass. Only merged statuses are reflected; no pending PR status or invented meeting history. Please link dated proof in the owner evidence index and preserve merge commits after the team freeze decision.


## 2026-11-20 - Christophe (C-31 existing-board merged-task refresh)

**Did:** Synced #91 to main e4090c6 and preserved shared logs. Refreshed only managed fields/cards on the existing private board #4: 92 tasks, no new cards, 93 updates; verified zero changes on a repeat. Original 3 manual cards, fields and status-column view #8 remain. Dated read-back receipt is web/board/evidence/refresh-2026-11-20.json.

**State:** C-31 doing. Web checks pass with 68 units/32 tools/types/build; branch shared docs/tasks 10 pass. Python tree matches C-35's final full root verification (710 tests, 93.14%, Ruff/format 162, mypy 85, schema/tasks). Current-head CI and independent review required; no new design/failure ID.

**Next / limits:** Review/merge the prepared board PR with a merge commit; record three genuine weekly team reviews separately. Only merged TASKS was mirrored; pending PR statuses and meetings were not invented. No duplicate board, manual field change, new feature scope or main push/self-merge.

## 2026-11-16 - Christophe, with Codex (C-29 setup verification and report draft)

**Did:** Updated isolated branch docs/c29-verified-setup-report to main 54d38c1. Corrected owned architecture/setup/provenance/API notes that still described setup as 501 before merged #87. Added synthetic per-browser clubs to the existing live fixture and four browser cases against the actual app factory, HTTP sessions and SQLite, without route replacement/interception. Covers redirect, skip, stop/reload/resume, completion, /me, empty Review, separate starter ticks and missing-CSRF/adviser 403. Drafted architecture, web, deployment and monitoring report sections in web/report/architecture-and-operations.md with source links and explicit local/provider/deployed evidence limits.

**State:** Small commits preserved; C-29 stays doing. Local root make-check equivalents pass: 681 tests, 93.11% coverage, Ruff/format (153 files), strict mypy (82 files), schemas/tasks. Web check: 68 unit and 12 board-tool cases, lint/format/types/build. Complete actual-API suite: 8 browser cases pass, including the four new setup cases on desktop/375px phone. Current-head remote CI and independent review remain required. D-126/F-227 were checked beyond main and all open-PR ranges. The new report/evidence files are owned; docs/evidence.md, docs/rubric-map.md, docs/api.md and README remain untouched for their owner.

**Next:** Tatiana reviews/incorporates the report sections and links their evidence in her index; Joey records a fresh README-only setup outcome. Respect the stated merge freeze: this batch is prepared for review, not self-merged. Use Create a merge commit when the team authorizes merge. C-35 has newly published route shapes in #95/#96, but those PRs and J-22 remain separate; do not call preview controls live.

**Open questions / blockers:** No actual deployment, Google/provider/ASME outcome or real producer instrumentation is claimed. F-151's one-tab setup limit and F-201's rejected-proposal retry reappearance remain. The test skips extraction and does not prove learning/consent/restart recovery. Windows junction cleanup unexpectedly affected shared dependencies; restored the original preview checkout with npm ci and installed independent dependencies/Python environment in this worktree. Successful rerun has no font warnings. Output stays untracked; the original C-35 checkout/preview branch is preserved.

## 2026-11-18 - Christophe (C-29 main sync)

**Did:** Merged current main 166f27e into #99, keeping both sides of the shared failure log and the original small report/setup commits. No report, application implementation or contract changed. Gmail fetch and J-22 guards are merged; candidate Inbox HTTP routes #95 remain open, so no new live-mailbox claim is added to the report.

**State / next:** Actual application/cookie/SQLite browser suite rerun: all 8 desktop/phone cases pass after sync. Full main-based Python gates are also verified in the parallel C-35 checkout (693 tests, 93.06%; Ruff/format, mypy, schema/tasks); C-29 current-head CI/review still required. C-29 remains doing until Tatiana reviews/incorporates the report and Joey records genuine README-only setup. Retain D-126/F-227, known F-151/F-201 limits, private-source/provider/deployment boundaries and independent review/merge commits. No self-merge under the stated freeze.


## 2026-11-20 - Christophe (C-29 current-main evidence and teammate attempt)

**Did:** Synced #99 to main e4090c6, retaining both sides of design/failure logs. Moved only C-29 D-126/F-227 to D-132/F-237 to avoid #103. Added a sourced receipt of Joey's README-only attempt, which stopped at the unavailable Docker Linux engine; updated report baseline and task progress. Historical handoffs remain unchanged.

**State:** C-29 doing. Final root gates: 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schema/tasks. Frontend quality/build: 68 units/12 tools. Actual app HTTP/cookie/SQLite setup/planning suite reran 8/8 on final main baseline; shared docs/tasks 10/10. Separate small sync, ID, receipt and verification commits preserved; current-head CI/review required.

**Next / limits:** Tatiana reviews/incorporates the report and owner evidence links; a teammate repeats the exact README flow when a working Linux container engine is available. Joey's attempt is a prerequisite failure, not completed app acceptance. Known setup limits F-151/F-201 and deployed/provider/ASME evidence remain separate. No new feature scope before 23 November, no authored backend/contract edit or self-merge/main push.

## 2026-11-19 - Christophe (C-13 session response validation)

**Did:** Isolated main-based fix/c13-session-response-validation validates the published /me view before rendering protected UI. Rejects unknown roles, malformed identity/club records, non-boolean flags and unsafe counts without coercion or demo fallback. Whitelists view fields and preserves valid independent role values. Generic recoverable error now has an accessible alert; explicit retry only rechecks reads. Added unit and desktop/phone HTTP regressions, first reproducing the unsafe unknown-role acceptance. No backend implementation, Python contract, auth method or server permission policy changed.

**State / next:** C-13 remains doing. Full root gates pass (693 tests, 93.06%; Ruff/format 158 files, mypy 84, schemas/tasks); web check 97 units/12 tools/types/build; HTTP 54 pass including 12 new cases; actual local API/cookie/SQLite 4 pass. D-129/F-233 reserved beyond main/open PRs. Small commits preserved; current-head CI/independent review still required. Merge via PR/merge commit, no main push or self-approval. Owner should link web/VERIFICATION.md and session tests from her evidence/rubric files.

**Open / limits:** Validated frontend response shapes do not establish server authorization, real Google login or deployed acceptance. C-35 remains separate. New development-tool advisory remediation is isolated as C-36, not mixed into this parser branch. Tatiana's new #95/#96 exact responses arrived during this work and unblock the next C-35 paid-read/Restore portion.


## 2026-11-20 - Christophe (C-13 approved-PR main sync)

**Did:** Merged main 0ac0b5b as Tatiana requested and retained both sides of the shared design-log conflict. Approved implementation and individual commits remain unchanged. Existing IDs checked across main/open PRs; no new IDs.

**State:** Web quality/build checks pass with 97 units and 12 tools. Python source/tests/scripts/schemas/lock match the C-35 checkout whose full root gates pass (700 tests, 93.09%); branch-local shared checks are run before publishing. Session response validation remains unchanged; deployed Google/every-screen acceptance is still open.

**Next / limits:** Tatiana re-approves the synced head after current-head CI and merges with Create a merge commit. No backend/auth contract change, real provider acceptance, self-merge or direct main push.


### 20 November follow-up - C-13, final Inbox main sync

**Did:** #95 merged as e4090c6 during verification, so merged that main as well. Retained each main/own failure once. C-35 preview role row moves to F-238; main's F-217 stays unchanged. C-29 D-132/F-237 avoid #103's IDs. Earlier dated references remain history.

**State / next:** Final root tree passes 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schema/tasks. The approved session validator is unchanged. Final Python source/tests/scripts/schemas/lock match the fully checked C-35 tree. Existing approved implementation and small commits remain. Re-review after final-head CI; Tatiana merges using Create a merge commit. No new scope before the 23 November meet-up or real mailbox/provider/deployed claim.

## 2026-11-12 - Christophe (C-35 disclosed inbox and deadline previews)

**Did:** Fetched main 2fff794; #76/#77/#78 are merged with their small histories preserved, and main CI is green. Claimed C-35 in a separate branch and built in small portions: ephemeral demo state, forwarding/verification and connection recovery, explicit paid-read confirmation, partial-failure retry, and separate deadline expiry/calendar/archive/Restore practice. Wired Inbox into desktop/mobile navigation, forwarding into Setup/Settings, lifecycle into Review. Existing HTTP Review payloads/policy remain unchanged; HTTP shows unavailable states without invented routes. TASKS names inbox list/capture paths, but JSON/error/retry and verification/lifecycle shapes still need Tatiana. Guide: web/INBOX_PREVIEW.md.

**Validation:** Root make-check equivalents pass: 667 passed, 1 skipped, 92.79% coverage; Ruff/format, strict mypy, schema and tasks. Web check passes: 74 units (6 new model cases), 12 board-tool cases, strict types/rehearsal types and build. Demo targeted suite: 24 passed across desktop/phone; final expanded accessibility/navigation/C-35 suite: 16 passed, including all 12 main routes. Two selected screenshots (phone forwarding, desktop adviser Inbox) visually inspected; no overflow/accessibility violations. HTTP suite: 42 existing cases passed; the 2 new fences passed after correcting an over-broad test interceptor that also matched /src/api modules. No app issue was hidden by that test fix. Windows default pytest temp access is restricted, so a fresh checked workspace output path was used. Browser teardown stalled under restricted process access; the normal-permission rerun completed. No real mail, Google/provider calls or billing/security/deployment claims.

**State / next:** C-35 stays doing, not production-ready: T-47 #92 and J-22 #93 are open; T-48/calendar contracts are pending, and D-115/D-116 live policy is after ASME. Need exact server shapes, validated adapter/HTTP stub tests against them and approved live acceptance. Independent review and final-head CI remain required; Create a merge commit and retain small commits. D-124/F-214-F-218 were reserved after all main/open-PR ranges. Tatiana should link owned guide/tests from her evidence/rubric docs. No outside-owner code or shared contracts changed.

## 2026-11-16 - Christophe (C-35 shared-ID correction)

**Did:** Fast-forwarded Tatiana's reviewed #94 branch update, then merged current main 54d38c1. Found that new #95/#96 reuse the preview's D-124/F-214/F-215 for different decisions/failures. Renumbered our rows to D-127/F-228/F-229 beyond #91 D-125/F-226 and #99 D-126/F-227; historical entries above remain unchanged. Updated web/INBOX_PREVIEW.md with the newly published candidate paths and the exact remaining response/proof contract gaps. No application behavior changed.

**State / next:** Preview stays demo-only and C-35 doing. Previous approved head 9691b69 had all five CI checks green. Shared task/log/failure checks are rerun for the correction; current-head full CI/re-review is required after push. Tatiana should supply concrete typed examples, Restore response and J-22 skip/retry/proof/settings shapes before strict live integration. Preserve commits and wait for the team's merge-freeze decision; no self-merge.

**Open questions / blockers:** #95/#96 are open, not production acceptance. No mailbox/provider access, paid calls or private data used. F-216/F-217/F-218 remain unchanged. The local demo preview is running again on 127.0.0.1:5173, still on the C-35 branch.

**Other updates:** C-31 board #4 is now readable and private, with 17 fields and three existing issue cards (#43/#83/#84). Manual statuses/Iteration and lack of management marker are incompatible with the importer; no changes, duplicate board or sprint history invented. #91 needs syncing and its access-blocker text refreshed. J-16 still needs explicit .github path ownership approval. C-14 note requests the deployed origin in Google, but no deployed URL or authorized configuration supplied. Team coordination and contract requests are in #43; assistants in other sessions must receive them through teammates.

## 2026-11-18 - Christophe (C-35 read-only HTTP metadata)

**Did:** Merged main 166f27e additively; preserved the new Gmail/J-22 rows. Added validated read-only Inbox waiting/skipped projections and independent UI error/refresh states against #95's candidate API table, without reading backend implementation. No body fields/HTML/links/storage, no demo fallback and no adviser resource requests. Paid capture, forwarding proof/settings and Restore remain unavailable. Work is split into task, adapter/unit, UI, browser/failure, guide and evidence commits.

**State:** Full root gates pass: 693 tests, 93.06% coverage, Ruff/format 158 files, mypy 84 files, schemas/tasks. Web check: 84 unit +12 board-tool cases/types/build. Full synthetic HTTP suite: 54 pass, including 12 targeted C-35 cases with accessibility/phone width. A root failure caught our initial F-230 collision with the merged Outlook guard; preserved that row and moved our boundary to F-232, then reran green. D-128/F-231 are new. Earlier F-216/F-230 handoff references are historical. Current-head CI/re-review remains required on #94.

**Next / limits:** Tatiana confirms concrete metadata types and supplies paid-capture skipped/outcome, Restore success and forwarding proof/settings contracts. Candidate #95 remains unmerged, so read-only HTTP can show an unavailable/error state on current main. Tests use intercepted synthetic responses, not a real mailbox/provider/security measurement. C-35 stays doing; no main push, self-merge or freeze override. Next free IDs are D-129/F-233 after rechecking main/open PRs. Ask the owner to link web/INBOX_PREVIEW.md and this verification entry in her evidence/rubric scope; no outside-owner documents were changed.

## 2026-11-19 - Christophe (C-35 clarified paid-read and Restore integration)

**Did:** Tatiana answered the exact API questions during this session (#95 ce1d514; #96 8dccd0e). Implemented single-message cost confirmation, synchronous duplicate-submit guard, no-fact/skipped acknowledgement and successful-fresh-snapshot gating before paid retries. Added HTTP current/archive filtering and president-only expired club-fact Restore with explicit date/no-end approval, matching acknowledgement and authoritative reload. Scoped public Restore 4xx explanations render as plain text; 5xx/unrelated errors remain generic. Forwarding proof/settings and Review expiry/calendar payloads are still unavailable. No backend implementation/contracts edited.

**State:** C-35 doing; scoped #94 changes are ready for independent review under the updated 23 November meet-up plan. Root gates pass: 693 tests, 93.06%, Ruff/format 158 files, mypy 84 files, schemas/tasks. Web check: 108 units/12 tools/types/build; full synthetic HTTP suite 82 pass (12 paid-read +16 Restore cases new), actual local API/cookie/SQLite 4 pass, demo Inbox/Knowledge 12 pass. D-131/F-235/F-236 checked beyond #100 D-129/F-233 and #101 D-130/F-234; earlier IDs remain historical. Original small commits preserved; current-head CI/re-review remains required.

**Next:** Tatiana reviews the frontend integration and publishes the remaining proof/settings plus Review expiry/calendar fields. Chris is reviewing #95/#96; no particular named reviewer is mandated, only someone other than the author. Before deploying, merge reviewed API/frontend changes with merge commits and verify actual Inbox/Restore routes using authorized synthetic/live acceptance. When combining #100 and #94, retain all session/inbox/Restore HTTP test files and both API adapter imports/sections.

**Open / limits:** New writes are tested with intercepted synthetic responses against candidate docs, not a real mailbox/provider or backend security-rate measurement; the actual API suite covers the existing plan/auth flow only. No exactly-once billing, durable browser retry, real Google configuration, ASME outcome or completed C-35 claim. Owner evidence/rubric files stay untouched; please link web/INBOX_PREVIEW.md and web/VERIFICATION.md. Separate #100 session guard and #101 development-dependency patch have all five CI checks green. No main push, self-merge or automatic approval of returned facts.


## 2026-11-20 - Christophe (C-35 requested main sync)

**Did:** Merged main 0ac0b5b into #94 as requested by Tatiana. Kept both sides of the sole conflict in the additive design log; all original small commits and T-48 entries remain. No authored backend/contract change. Audited decision/failure numbers against main and every open PR; no new row needed.

**State:** C-35 doing. Root checks pass: 700 tests, 93.09%, Ruff/format 159 files, mypy 84 files, schema/tasks. Frontend quality/build: 108 units and 12 tools. HTTP browser suite: 82 pass. Current-head CI and fresh independent re-approval are required after push.

**Next / limits:** Tatiana re-approves the synced head and merges with Create a merge commit. T-48 is on main; #95 still supplies the unmerged Inbox routes. Forwarding proof/settings and Review expiry/calendar payloads remain separate. Existing write tests use synthetic interceptions, not actual mailbox/provider/deployed acceptance. No self-merge or direct main push.


### 20 November follow-up - C-35, final Inbox main sync

**Did:** #95 merged as e4090c6 during verification, so merged that main as well. Retained each main/own failure once. C-35 preview role row moves to F-238; main's F-217 stays unchanged. C-29 D-132/F-237 avoid #103's IDs. Earlier dated references remain history.

**State / next:** Final root tree passes 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schema/tasks. All 82 HTTP cases passed in a completed run with normal Windows process cleanup. Frontend source/tests/lock are unchanged by the second main sync. Existing approved implementation and small commits remain. Re-review after final-head CI; Tatiana merges using Create a merge commit. No new scope before the 23 November meet-up or real mailbox/provider/deployed claim.


## 2026-11-20 - Christophe (C-31 after reviewed Inbox merge)

**Did:** Tatiana merged #94 and Joey's #102 as main 0f3bb09. Synced this existing PR, retaining both shared logs and every earlier handoff/evidence line. Original focused commits stay intact; no new feature scope or design/failure IDs.

**State:** Frontend checks pass: 108 units/32 tools, lint/format/types/build and branch-local shared docs/tasks. Shared Python-tree root gates pass: 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schemas/tasks. Board refresh source/read-back and zero-change repeat are in the new follow-up receipt; three real weekly-review records remain open.

## 2026-11-20 - Christophe (C-29 after reviewed Inbox merge)

**Did:** Tatiana merged #94 and Joey's #102 as main 0f3bb09. Synced this existing PR, retaining both shared logs and every earlier handoff/evidence line. Original focused commits stay intact; no new feature scope or design/failure IDs.

**State:** Frontend checks pass: 108 units/12 tools, lint/format/types/build and branch-local shared docs/tasks. Shared Python-tree root gates pass: 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schemas/tasks. Report/setup evidence and the blocked README-only receipt remain intact; successful fresh complete-app acceptance is still open.

**Next / limits:** Fresh independent review after current-head CI, then a merge commit. Existing deployed/provider/club acceptance gaps remain separate; no authored backend/contract edit, new scope, self-merge or main push.

## 2026-11-20 - Christophe (C-13 combined session/Inbox integration)

**Did:** Synced #100 to reviewed #94/#102 main 0f3bb09. Kept both adapter imports, all session/Inbox/Restore HTTP registrations and demo exclusions, both API notes sections and all previous shared handoff/evidence lines. Original commits retained; no new scope or D/F IDs.

**State:** Frontend checks pass: 137 units/12 tools/types/build. Clean standalone HTTP suite: 94 pass; sequential actual local API/cookie/SQLite: 4 pass. Shared Python root gates: 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schemas/tasks. Branch shared docs/tasks: 10 pass. Overlapped artifact failures and fresh uv certificate/startup preparation were resolved by normal sequential runs using the system trust store, not assertion/source changes.

**Next / limits:** Fresh independent approval after current-head CI, then merge with Create a merge commit. Deployed Google/every-screen acceptance remains open. No real provider/private inputs, backend/contract implementation changes, new scope before 23 November or main push/self-merge.


## 2026-11-22 - Christophe (C-31 pre-meet-up sync and board verification)

**Did:** Synced #91 to main 60d7027, retaining shared rows and every earlier handoff/evidence line. Refreshed existing private board #4 from merged TASKS only: 92 tasks, no new cards, 92 updates; repeat zero changes. Original three manual cards, fields and status-column view #8 remain. New dated receipt is web/board/evidence/refresh-2026-11-22.json; prior receipts preserved.

**State:** C-31 doing. Web checks pass: 137 units/32 tools/types/build; branch shared docs/tasks 10 pass. Identical Python tree passes root gates with updated locked dependencies: 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schemas/tasks. Fresh independent re-review and current-head CI required; original commits retained.

**Next / limits:** Re-review/merge with Create a merge commit for 23 November, then record actual weekly reviews separately. No unmerged task states, meeting history, deployed/provider/club acceptance, new scope, D/F IDs, main push or self-merge invented.


## 2026-11-22 - C-31 weekly-review bonus withdrawn by owner

Christophe explicitly chose not to pursue the weekly-review/sprint bonus. D-133
and the current TASKS entry record that decision; the existing board remains an
ordinary task tracker. Earlier receipts and missing-record statements are retained
as history, not active acceptance requirements or proof of earned bonus credit.
No further meeting-record collection, bonus-driven refresh or board deletion.
The existing tracker PR stays reviewable; no weekly-review completion is claimed.
This is a docs/scope-only update; shared task/log checks and formatting pass.


## 2026-11-23 - Christophe (C-31 restored weekly practice and native bulk repair)

**Did:** Restored C-31 per Christophe, superseding D-133 with D-137. Built the explicit native-field planner/adapter/CLI and 10 new regressions (F-248), kept existing option/iteration identities and card content, and linked commit-history summaries for the four owner-reported Mondays. Executed one authorized bulk run: canonical task mirror plus native status/assignees/Monday iterations/priority/size/points and all 3 issue statuses. No invented attendance, oral decisions or original assignments.

**State:** Live read-back: 93 task cards +3 issues, 542 native mutations, zero remaining native changes; existing views/private board preserved. Issue #43/#84 assigned Christophe, #83 Tatiana, all In progress. Receipt: web/board/evidence/native-fields-2026-11-23.json. Web checks: 137 units/42 tools/types/build; shared checks 10 pass; root baseline 728/93.21%, Ruff/format 162, mypy 85, schemas/tasks. Focused source commits preserved; current-head CI/re-review required.

**Next / limits:** Review/merge #91 and the restored report scope in #99 with merge commits. Maintain native fields after reviewed TASKS changes using npm run board:reconcile; default plan is read-only. User-reported dates and commit history do not prove undocumented decisions; estimates are current planning points. No second bulk mutation run, new backend contract, real data, model calls, main push or self-merge.


### 23 November shared-ID correction

The final fetch found #112 had allocated F-248 during the native-board work.
Preserved that owner's row and moved our native reconciliation regression to F-249.
D-137 is still unique. Earlier dated F-248 references above describe the work before
this correction. Native source behavior/live read-back are unchanged; shared checks
and formatting pass after renumbering. Next free IDs: D-138/F-250 after rechecking.

## 2026-11-22 - Christophe (C-29 reviewed-session and dependency sync)

**Did:** Synced the existing PR to main 60d7027 after #100 and the Python dependency updates merged. Kept all shared rows and earlier handoff/evidence lines, retaining individual commits. No new scope or design/failure IDs. All eight actual local HTTP/cookie/SQLite setup/planning cases passed with FastAPI 0.162.5. Report prose now links the merged session validator and HTTP regressions; real Google/hosting/ASME acceptance and the blocked README-only attempt remain explicit.

**State:** Root locked-environment gates pass: 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schema/tasks. Web quality/build: 137 units/12 tools; branch shared docs/tasks 10 pass. Original acceptance limits remain open; fresh-head CI and independent re-review are required.

**Next / limits:** Re-review the synced PR, then Create a merge commit for the 23 November meet-up. No new backend/auth contract, model calls, real data, main push or self-merge. Genuine deployment/club/weekly-review acceptance is not inferred from these tests.


### 22 November owner scope update

Christophe has dropped the weekly-review/sprint engineering bonus. The report now
excludes that claim and no longer lists three meeting records as pending acceptance.
Keep the existing board as an ordinary task tracker. C-29's fresh README-only setup,
report incorporation and deployed/provider/club acceptance limits remain unchanged.
D-133 and the narrowed tracker task are in #91; no other engineering bonus was cut.


## 2026-11-23 - C-29 restored weekly practice and sourced board context

**Did:** Synced main 2bb9f5e, preserving the actual setup row and main's sourced
inbox/audience/expiry documentation. Restored weekly-practice reporting after
Christophe reversed D-133 (D-137 in #91). The report links #91's repository-history
summaries and attributes four Monday dates to Christophe; it does not infer
attendance, oral decisions or original assignments from commits.

**State:** Web quality/build passes: 137 units and 12 tools. Actual local
HTTP/cookie/SQLite setup suite: 8/8. Shared tasks/log/failure checks: 10 pass.
Merged Python baseline gates: 728 tests, 93.21%, Ruff/format 162 files, mypy
85 files, schemas/tasks. Report remains doing; fresh README-only success,
report incorporation and actual deployed/provider/club acceptance remain open.

**Next / limits:** Fresh independent review and current-head CI, then a merge
commit preserving the focused history. #91 performs the separately authorized
native-field bulk correction. No real club inputs, paid model calls, invented
meeting decisions or main push/self-merge.

## 2026-11-19 - Christophe (C-36 development dependency audit)

**Did:** Isolated fix/c36-minimatch-audit from main 166f27e after npm audit found GHSA-g3hv-75wg-m249 through the ESLint/TypeScript-ESLint development chain. npm-compatible lock updates resolve minimatch 11.0.9, ESLint 10.15.0, TypeScript-ESLint 8.73.0 and config-array 0.23.6 without force/overrides or application dependency-range changes. Structural comparison proves every production lock entry is unchanged. Added npm run audit:dependencies as an explicit full development-inclusive audit regression command; no workflow files changed.

**State / next:** C-36 review. Clean npm ci and both full/production-only audits report zero findings (previous full audit: nine affected development package nodes; production-only zero). Web check: 68 units/12 tools/types/build and lint/format pass. Full root gates: 693 tests, 93.06%; Ruff/format 158 files, mypy 84, schemas/tasks. Advisory and reproducible commands: web/security/dependency-audit-2026-11-19.md. D-130/F-234 reserved after C-13 D-129/F-233. Await current-head CI and independent review; preserve small commits and merge commits. Owner should link evidence in her index.

**Open / limits:** This is a tooling dependency remediation and live advisory scan, not a production incident or measured security-rate result. The audit needs registry connectivity and its database changes over time. Windows uses the trusted system CA store with certificate validation enabled. No backend implementation/contracts, real club data, credentials, source text or provider calls involved. C-13 session validation and C-35 integration remain independent PRs.


## 2026-11-20 - Christophe (C-36 approved-PR main sync)

**Did:** Merged main 0ac0b5b as Tatiana requested and retained both sides of the shared design-log conflict. Approved implementation and individual commits remain unchanged. Existing IDs checked across main/open PRs; no new IDs.

**State:** Web quality/build checks pass with 68 units and 12 tools. Python source/tests/scripts/schemas/lock match the C-35 checkout whose full root gates pass (700 tests, 93.09%); branch-local shared checks are run before publishing. Full development npm audit remains at zero vulnerabilities; production application dependencies are unchanged.

### 20 November follow-up - C-36, final Inbox main sync

**Did:** #95 merged as e4090c6 during verification, so merged that main as well. Retained each main/own failure once. C-35 preview role row moves to F-238; main's F-217 stays unchanged. C-29 D-132/F-237 avoid #103's IDs. Earlier dated references remain history.

**State / next:** Final root tree passes 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schema/tasks. The development dependency patch is unchanged; full npm audit remains zero. Final Python source/tests/scripts/schemas/lock match the fully checked C-35 tree. Existing approved implementation and small commits remain. Re-review after final-head CI; Tatiana merges using Create a merge commit. No new scope before the 23 November meet-up or real mailbox/provider/deployed claim.

## 2026-11-20 - Christophe (C-36 after reviewed Inbox merge)

**Did:** Tatiana merged #94 and Joey's #102 as main 0f3bb09. Synced this existing PR, retaining both shared logs and every earlier handoff/evidence line. Original focused commits stay intact; no new feature scope or design/failure IDs.

**State:** Frontend checks pass: 108 units/12 tools, lint/format/types/build and branch-local shared docs/tasks. Shared Python-tree root gates pass: 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schemas/tasks. Full npm dependency audit reports zero vulnerabilities. The patched lint chain checks the now-merged Inbox/Restore frontend.

**Next / limits:** Fresh independent review after current-head CI, then a merge commit. Existing deployed/provider/club acceptance gaps remain separate; no authored backend/contract edit, new scope, self-merge or main push.

## 2026-11-22 - Christophe (C-36 reviewed-session and dependency sync)

**Did:** Synced the existing PR to main 60d7027 after #100 and the Python dependency updates merged. Kept all shared rows and earlier handoff/evidence lines, retaining individual commits. No new scope or design/failure IDs. Full and production-only npm audits both report zero vulnerabilities on 22 November. An initial sandboxed registry/cache request failed; the normal registry-access retry used the system trust store and a writable workspace cache. No audit exception, package update or TLS bypass was needed.

**State:** Root locked-environment gates pass: 710 tests, 93.14%, Ruff/format 162 files, mypy 85 files, schema/tasks. Web quality/build: 137 units/12 tools; branch shared docs/tasks 10 pass. Original acceptance limits remain open; fresh-head CI and independent re-review are required.

**Next / limits:** Re-review the synced PR, then Create a merge commit for the 23 November meet-up. No new backend/auth contract, model calls, real data, main push or self-merge. Genuine deployment/club/weekly-review acceptance is not inferred from these tests.


## 2026-11-23 - Christophe (C-36 current-main conflict resolution)

**Did:** Merged main 9b12718 into #101; kept both unique design/failure rows and
all earlier handoff/evidence lines. Preserved the separate C-29 and C-36 entries
as complete sections rather than splicing their headings and paragraphs. Original
focused commits and the development-only lockfile remediation remain intact.

**State:** Python gates pass: 733 tests, 93.16% coverage, Ruff/format 162 files,
mypy 85 files, schemas/tasks. Web checks pass: 137 unit tests, 12 board-tool tests,
lint/format/types/build. Full and production-only npm audits report zero; production
lock records match current main. C-36 stays review pending current-head CI and
fresh independent approval.

**Next / limits:** Tatiana re-reviews the synced head and merges with Create a
merge commit once CI is green. #91 already contains current main and all five
checks pass; #99 is already merged. Independently reviewed #104 and requested
corrections to approval roles, unknown-audience fallback and C-27 human scoring.
No new scope, provider calls, private inputs, direct main push or self-merge.


## 2026-11-23 - C-36 formatting check correction

**Did:** Fixed the actual Web CI failure: the final appended VERIFICATION.md
entry had not been formatted after the earlier local check. Merged approved
#91 main 5c66db9, preserving both failure-log sides and existing commits.

**State:** Rerun full web checks after formatting; current-head CI and fresh
independent C-36 approval remain required. No application/dependency change.

**Next:** Review the corrected CI head before merge. #91 merged by explicit
Chris request with its current-head independent approval and five green checks.
Reviewed #81/#82 separately; their draft measurement limitations remain open.


## 2026-11-23 - C-36 duplicate-ID CI correction

**Did:** Inspected the final-head failed Python CI: both failing assertions found
the duplicate F-249 inherited from main, not a frontend failure. Merged main
b23e9d4 including Tatiana's reviewed #122 correction (suggested-edit row and its
test docstring become F-260; the board keeps F-249). No new IDs or runtime edits.

**State:** All 10 task/failure/log-number checks pass from this worktree's own
working directory; task validation, verification formatting and 42 board-tool
tests pass. Previous head's Web quality, browser/API, container and dependency
checks were green. Fresh combined-head CI and independent re-approval remain.

**Next:** Re-approve after the new CI run, then merge with a merge commit.
Azure deployment continues separately; no direct main push or self-merge.


## 2026-11-23 - Christophe (C-37 guided cabinet handover)

**Did:** Replaced the permanent Handover nav item with a contextual Start your
role entry, four navigation-highlight steps, pause/resume/skip/replay, one sourced
reference entry and an expandable guide. Settings exposes cabinet preparation;
outgoing notes remain explicit Teach submissions. Role-learning Ask questions
include inspectable session-role/step context only after opt-in; Teach is unchanged.
Fixed member/role remounts, invalid saved progress, storage-denial handling, phone
highlighting, heading structure and unavailable live sign-off controls in self-review.

**State:** Synced reviewed mail/calendar main 1d162df, preserving both shared logs;
D-140 and F-269-F-271 avoid main's new IDs. Locked Python gates pass: 834 tests,
1 expected failure, 93.63% coverage; Ruff/format 176 files, mypy 87, schemas/tasks.
Web quality/build passes: 142 units, 42 board tools, lint/format/strict types.
Broad browser checks: 50 demo, 98 HTTP plus four rehearsal cases rerun on their
required origin, and eight real local API/cookie/SQLite cases. After main sync,
the eight new role cases and four reference/Knowledge cases pass again; the real
API suite is rerun on a fresh server. Visually inspected desktop/phone captures.

**Next:** Independent Tatiana/Joey review, current-head CI, then a merge commit.
Owner integration proposal is web/GUIDED_HANDOVER.md. Browser-local progress is
not cross-device/term persistence or an invitation. The Ask endpoint still has
its documented placeholder until J-15: this prepares questions, not verified
model tutoring. No invented routes, changed backend contracts, automatic AI calls,
new membership authority or deployed Azure acceptance claim. Coordinate T-33
before evaluating this different experience. Existing Azure deployment is unchanged.


## 2026-11-24 - Christophe (C-35 expiry follow-up to #128)

**Did:** Audited already merged #147/#148: expiry editing exists on Review,
but Knowledge detail and comparison-side expiry were missing, dates omitted years,
and bulk approval ignored date/notice drafts. Added common validity labels and a
source-check hint for dated/term text with explicit null expiry. Missing server
metadata is visibly unavailable, never treated as permanent. Changed metadata
and undated hinted facts stay out of bulk approval; read-only clear is disabled.
D-250/F-500/F-501 checked against main and every open PR.

**State:** Root gates pass: 910 tests, 93.67% coverage; Ruff/format 181 files,
mypy 89 files, schema/task validation. Dependency lockfiles match the verified
C-37 environment used for these checks; current source resolves from this worktree.
Frontend quality/build, 145 units and 42 board-tool tests pass.
70 desktop/phone HTTP contract/Restore cases plus two adviser expiry/card Axe
cases pass. A full-page adviser Axe scan also found existing account-summary
name and read-only-strip landmark issues; the new card scan is scoped to the card. These use synthetic intercepted API data,
not a deployed API, university rule or live provider. C-35 remains doing for its
broader unfinished integration/acceptance scope.

**Next / owner question:** Tatiana: #128 also asks to edit expiry after approval.
The published Knowledge edit contract in docs/api.md accepts text/lead_time_days
only, so this PR does not invent valid_to support there. Please publish the field,
clear-vs-absent semantics and permission/undo behavior; Chris can then wire that
last input. Existing Review valid_to payload is unchanged. No backend-owned file,
real club data, external model call, direct main push or deployment change.


## 2026-11-24 - Christophe (C-35 current ID allocation)

**Did:** Corrected this open PR to the newly allocated Christophe range in main
AGENTS.md: D-250 and F-500/F-501. Earlier provisional IDs were not merged.

**State / next:** Previous head has all five CI checks green. Chris reports
Tatiana temporarily waived independent review/approval to keep work moving;
continue with PRs, merge commits and green checks under that session exception.
This changes repository review timing only. App authorization and data approvals
remain governed by the published contracts.


## 2026-11-24 - Christophe (C-35 accessibility follow-up)

**Did:** Fixed both findings recorded above: account summary uses its visible
member/role content plus a screen-reader account prefix instead of an overriding
label; avatar initials are decorative. Adviser access notice is a named region.
The adviser expiry test now scans the entire page, without rule exclusions.
F-502 records this correction; D-250/F-500/F-501 are the expiry IDs.

**State:** Desktop/phone full-page adviser Axe and sign-out tests pass. Frontend
quality/build checks and shared log/task validation are rerun before publishing.
Previous full root gates passed 910 tests at 93.67% coverage; Python/contract
code is unchanged. Five green checks on the prior head are historical, not proof
of the final head. The post-approval Knowledge expiry API question remains open.

**Next:** Current-head CI, then merge using the temporary review waiver Chris
relayed in this session. Keep commit history. No main push or deployment change.


### C-29 final reconciliation

#152 merged as 62d1787 with all five current-head checks green under Chris's
reported temporary review waiver. Synced that main, retaining every C-35/C-29
handoff entry. C-36/#101 and C-37/#123 now read done based on actual merges and
existing independent reviews; their historical progress notes remain intact.
All root gates pass on the documentation update: 910 tests, 93.67% coverage,
Ruff/format 181 files, mypy 89, schemas/tasks. Four updated documents have valid
local links and the web guide passes formatting. C-29 remains doing for its
unverified acceptance/report work; no live provider or deployment claim added.


### C-29 report follow-through

Updated the owned report draft as well as its source guides, including trusted-mail
exceptions, guided handover, live chat wiring and the completed expiry merge.
Recorded only the observed public 200 login / 401 unauthenticated API responses;
SSH timed out, so the running image and any deployment change remain unverified.
The SPA fallback is explicitly not an API-health check. No raw URL/account/key
or real club record is copied into the report. Rechecked report links/formatting.

## 2026-11-25 — Tatiana, with Claude (ui/impeccable-audit-fixes)

**Did:** T-50 (D-158): text floor of 12 px in `styles.css`, 44 px touch targets under `pointer: coarse`, the decorative eyebrow labels removed from pages (kept where they carry data: 404, event revision, knowledge scope, source excerpt, role tour step), focus ring colour darker. Audit file: Tatiana has it (`ui-audit-2026-11-25.md`).

**State:** `npm run check` passes in `web/` (lint, format, 145 unit tests, types, build). The browser tests and a look at the pages were not run: no browser was available in the session. Christophe's review should include opening each screen on desktop and at 375 px, mainly the sidebar footer, mobile nav and the demo strip, where the old text was 8 to 9 px and may now wrap or crowd.

**Next:** Christophe opens the screens and runs `npm run test:e2e`; fix any layout that wraps badly. After the freeze: map the 378 hard-coded colours to the variables, replace the side-stripe borders.

**Open questions / blockers:** Contrast of the darker focus ring and the final look are unchecked by eye.



## 2026-11-25 - Christophe (C-38 UI cleanup; C-18/C-35 host prerequisite)

**Did:** Applied Chris's design direction in small commits: removed the workspace
marketing hero/fake preview, page eyebrows and repeated subtitles, sidebar/footer
slogans and static season badge; simplified login and role-tour entry. Events use
flat working rows, with neutral surfaces and fewer tinted/rounded icon containers.
Preserved event revision and Knowledge scope/kind as ordinary contextual metadata.
Merged parallel T-50 #164/#165, keeping its text floor, focus ring and touch targets.
D-251/F-503 describe the boundary. One chat regression now uses the shorter heading.

**State:** Browser/workflow/accessibility and root gates run on the merged tree
before publication; synthetic desktop/phone captures are inspected separately.
Temporary local server/config/artifacts are not part of the PR. C-38 does not
change transport, model, source authority or app approval rules.

**Host task:** #160/#161 are merged and their docs/api.md fields are available.
Direct SSH still times out; DNS and a separate TCP check confirm the target but
not access. Chris is checking the Azure SSH rule. Credential files validate as
web clients without printing their values; they remain untouched until securely
applied to the existing host environment. No secret copied to Git/logs, host edit,
container recreation, login repair, OAuth callback or download deletion is claimed.
C-35 connection buttons remain after that explicitly requested host-first step.

**Next:** Finish current-head UI checks and publish for review. Resume host access,
preserve its existing Gmail refresh token, configure clients and check the private
president membership/build-client consistency, then implement the connection UI.


### C-38 verification

Merged 2784fb0; locked own .venv with all extras passes 949 tests, 93.76%
coverage, Ruff/format 187 files, mypy 92, schemas/tasks. Web checks pass 145
units/42 board tools plus lint/format/types/build. Stable final-layout runs pass
50 desktop/phone demo/workflow/Axe cases and 64 HTTP contract/role-learning cases.
Inspected synthetic desktop/phone Events, sign-in, Review, Knowledge and Chat
captures; these are local artifacts, not deployed or real-provider acceptance.
One final draft icon/404 copy polish is checked by web quality gates. Earlier
interrupted/HMR runs are not reported as successful checks. C-38 is review.


## 2026-11-26 - Christophe (C-35 urgent Google connection controls)

**Did:** Per Chris's urgent request, built the #160/#161 frontend separately
from blocked SSH. Calendar and Settings use the connection status and president
Connect/Disconnect. Inbox uses operator status/Connect/Disconnect and cabinet
free Fetch, counts-only feedback, fresh lists and a scoped plain 409. Callback
messages do not establish a connection; Google auth URLs are narrowly validated.
No connection/fetch controls for advisers; opening pages makes no mutation.
Disconnect requires explicit confirmation. D-252/F-504/F-505.

**State:** Ten new synthetic desktop/phone HTTP cases pass, including Google
navigation interception, all states, role controls, callbacks, cancel/confirm,
fetch/error privacy and Axe. Web quality/build initially passes with the adapter
units. Further regression/root gates and final-head CI are run before completion.
No real Google consent, email read, provider call or private data is used in tests.

**Host / acceptance:** SSH still times out. No environment lines applied,
container recreated/restarted, downloaded file deleted, member lookup/repaired,
or build/server Google client ID comparison is claimed. Public login responds
200 and unauthenticated /api/me 401; /api/openapi.json returned 500 on the observed
host. None of these prove sign-in, president role or deployed commit/#163.
The last image this assistant deployed was 5c66db9; the current image is unknown.

**Next:** Publish the button PR now; finish all current-tree checks. Restore
administrative access, preserve host env/refresh token, apply supplied credentials,
recreate the intended container and verify its image/version plus actual phone
Google login/president /me. The returned fetch `refreshed` field is not displayed:
docs/api.md does not specify its type/meaning; queued/skipped/not_for_a_club counts
are displayed without guessing it. Tatiana can clarify that nonblocking detail.


### C-35 regression follow-up

Root gates pass: 949 tests, 93.76% coverage; Ruff/format 187 files, mypy 92,
schemas/tasks. Web checks pass 151 units and 42 board-tool tests. Broad HTTP
run passes 116 cases; the two stale denial assertions were corrected from two
to three independent unavailable resources (Gmail status is new) and both rerun
cases pass. Strict metadata, role-tour and rehearsal fixtures now explicitly
serve the new published GET states; unknown mutations remain rejected. Final
combined CI is required. The current PR is #167; initial failed CI was the stale
fixture expectations, not evidence of host configuration or Google acceptance.

## 2026-11-26 - Christophe (C-18/C-35 Azure host verification)

**Did:** #167 merged at main 4722838. Patched only the requested OAuth,
operator and sender keys in the existing host environment file, preserving
unrelated settings. No legacy Gmail refresh token existed. Recreated the actual
Compose app, backed up four SQLite databases privately, built the production
image from that fixed merged SHA and replaced the app image. The requested
president membership was missing; added with the provided CLI and verified.
Deleted both supplied OAuth JSON downloads after effective runtime verification.
The Azure inspection session is closed; credentials were passed as protected
parameters and never printed or committed. Added the Azure update runbook.

**State:** Running image clubops:4722838 has full revision label
4722838c3d2f371cfcbd6076cd689fc013821fe8 and is healthy. This includes #163.
Runtime settings match Compose; server sign-in ID matches built JS/build ID;
dev login is disabled and secure cookies enabled. Public login returns 200;
unauthenticated /api/me, Calendar connection and Gmail status return 401.
Served assets contain all three connection/fetch calls. All five #167 checks
passed. Documentation formatting passes; root checks are recorded below.

**Next:** Account owner tests real Google sign-in on a phone and confirms their
club/president role, then explicitly connects Calendar and operator Gmail.
Confirm the exact deployed Gmail callback in Google's console: it was absent
from the supplied download, while Calendar's callback was present. Downloads
can be stale; no Google-console change is inferred. Administrative membership,
public smoke tests and synthetic phone tests do not prove real sign-in, consent,
mailbox fetch or event-planning acceptance. C-18/C-35 remain doing for those gates.
No live mail/model call, calendar write, data restore or disaster-recovery success
is claimed. Host metadata and follow-up are posted on merged #167.

### C-18 verification

Root make-check equivalent gates pass on this merged source: 949 tests,
93.76% coverage, Ruff/format 187 files, mypy 92 files, schemas and task validation.
Used the verified locked environment with matching uv.lock and this worktree's
source path. Documentation formatting and git diff whitespace checks pass.
This follow-up changes task/handoff records and the deployment runbook only;
#167's five green CI checks cover the deployed implementation. No new contract,
design decision or failure mode is introduced here.

## 2026-11-26 - Christophe (C-35 connection-label follow-up)

**Did:** Checked the reported two literal question marks and changed them to
an em dash in the host-configured status and an ellipsis in the Fetch loading
label. Used Unicode escapes to preserve the characters across shell encodings.
These two lines are a separate commit on deployment follow-up PR #168.

**State:** Frontend check passes (151 units, 42 board-tool cases, lint, format,
types and production build). All ten existing synthetic desktop/phone Google
connection cases pass; shared dependency junction caused local Vite font warnings,
so these results establish workflow/accessibility checks, not final font rendering.
Root gates passed earlier on this branch (949 tests, 93.76%); no Python changes.
Public HTTPS login is still 200; protected status endpoints require sign-in and
the deployed bundle contains the connection controls. Chris reports the account
owner said access worked; separate Calendar/Gmail consent outcomes are unspecified.

**Next:** Review/merge #168, then include the two-label polish in the next host
release; this session did not redeploy or change working host settings. The supplied
host script was inspected, not executed: it assumes .env and a default Compose
project, whereas the observed host uses production.env, compose.yaml and the named
clubops-prod project. The prior deployment used protected parameters for secrets,
not plaintext credentials in script text. Google-console callback verification
and account-owner live connection acceptance remain as recorded above.

## 2026-11-26 - Christophe (C-18/C-35 requested redeploy)

**Did:** Chris explicitly requested redeployment while #168 remained open.
After all five checks passed on head 6749fb0, deployed that exact SHA without
merging or pushing main. Created seven private SQLite backups, built the
production image and replaced only the app container. Every existing resolved
runtime environment setting was verified against the new container; no OAuth
setting, membership, secret or stored connection was changed by this release.

**State:** Actual running image is clubops:6749fb0, revision
6749fb00ea8efeabeabb682f0786a0b4ef85ea51, healthy. Fresh Azure inspection confirms
OAuth keys present, matching frontend/server sign-in IDs, dev login disabled and
secure cookies enabled. Public HTTPS login returns 200; unauthenticated /api/me,
Calendar connection and Gmail status return 401. Served JS contains the corrected
host separator and Fetch ellipsis, with the old Working? string absent. Managed
inspection requests were given a fresh source marker to force new execution.
The temporary Azure session is closed. This commit adds deployment records only.

**Next:** Tatiana tests her own Calendar/Gmail connections on the live site and
reviews/merges #168. Do not treat the deployed PR head as already merged into main,
or these public/host checks as real Google consent, mail fetch or event acceptance.
No external provider operation was triggered by the redeploy checks.

## 2026-11-26 - Christophe (C-31 current backlog maintenance)

**Found / changed:** Read-only preview stopped before mutation because legitimate
issues #128/#129/#169 had been added beyond the original three manual handoffs.
Registered those explicit primary owners, retaining original handoffs and refusing
unknown/duplicate/foreign cards. Existing issue assignees are added to, not removed;
card content and underlying state stay unchanged. #128's shared API/web ownership
is not transferred by its primary board assignment. D-255/F-510.

**Verified:** All root gates pass: Ruff/format 187 files, mypy 92, schemas/tasks,
949 tests, 93.76% coverage. Matching locked dependencies reused. Full web checks
pass: lint/format, 151 units, 43 board-tool tests, rehearsal types and build.
The regression covers new closed/open issue mapping, preservation and refusal of
unknown/duplicate/foreign issues. No app/UI/provider behavior changes.

**Live run:** One explicit bulk invocation pinned to merged main 4722838 verified
98 task cards and six issue cards: five tasks created, 118 mirror updates,
59 native updates, zero remaining native changes. #128 Done/Christophe;
#129 and #169 In progress/Tatiana. Existing content, assignments, views and
iteration identities preserved. Reviewed metadata receipt is
web/board/evidence/native-fields-2026-11-26.json; raw inventory stays ignored.

**Next:** Independent PR review and merge commit; C-31 remains doing for team
review. Board deliberately excludes unmerged #153 task corrections and #170's
turnover task. After those merge, reconcile again from the new exact main.
The four Monday dates remain owner-reported, not inferred meeting decisions.
Tatiana: #169 needs the atomic turnover API contract; report/grading handoff is
in #153 (all five checks green). No claim of completed final evaluation, live
provider acceptance, production telemetry or backup restoration.

## 2026-11-27 - Christophe (C-31 sync after #168)

**Did:** Merged main b3ce74e after #168. Resolved the handoff conflict by
retaining every complete branch section and every main deployment/verification
section; checked that no section heading from either side was lost. Existing
task statuses and dated receipts are retained. No backend contract, host setting
or live provider operation changed as part of this merge.

**Verified:** Required root gates pass: Ruff/format 187 files, mypy 92, schemas
and task validation; 949 Python tests, 93.76% coverage. Full web quality/build
checks pass (151 units and 43 board-tool tests), lint/format, rehearsal types
and production build. Matching locked dependencies used. Current-head GitHub CI
will run after this sync is pushed; prior green checks are historical.

**Next:** Independent owner review and merge commit after all fresh checks pass.
Chris requests a verified current-main redeploy whenever this assistant merges
to main; that operational step is separate from syncing a PR branch. Calendar
Connect remains under C-18/C-35 diagnosis: saved 26 November host comparisons
match the supplied ID/redirect, but current Google-console values and the
callback's exact failure stage are not yet established. Owner handoff is #83.

## 2026-11-27 - Christophe (C-31 follow-up sync after #172/#153)

**Did:** Merged main 8828847 after the Calendar owner-check fix and #153's
grading/docs merge. Kept every complete handoff section from both parents,
including the longer C-29 reconciliation entry. A local failed resolver was
corrected before publication; the final merge contains no conflict markers.

**Verified:** All required root gates pass: Ruff/format 187 files, mypy 92,
schema/task validation, 949 tests and 93.74% coverage. Full web checks pass:
151 units, 43 board-tool tests, lint/format, rehearsal types and production build.
Fresh GitHub CI is required on the follow-up head. No board mutation, provider
action or host deployment occurred in this merge. The Calendar fix is now in
main; deployment is queued pending renewed Azure authorization.

## 2026-11-24 - Christophe (C-29 current integration documentation)

**Did:** Reconciled owned architecture, data provenance and memory guides with
main eae20c5's published decisions: trusted clean new mail facts can apply, while
overrides/merges and flagged facts need Review (D-151); dated mail deadlines have
a separate calendar path (D-150); chat wiring and dated sources are merged
(D-200/#149); chatbot ratings use a private human-marked sheet (D-152/#151).
Updated the guided-handover integration status without claiming persistent tutoring.

**State:** Documentation only; no backend implementation read or changed, no
new runtime policy or contract. Checked statements against owner decisions/API,
kept the paid-read/scheduling distinction and missing Knowledge expiry-edit field
explicit. C-29 stays doing for report incorporation and fresh/deployed acceptance.
Local links, web guide formatting and shared task/log checks run before publication;
full root gates use the same locked dependencies as the verified main source.

**Next:** Publish a separate C-29 PR, preserve small commits, merge after green
checks under Chris's temporary review waiver. Tatiana owns the stale chat/setup
availability notes in docs/api.md and the expiry-edit API extension. No completed
private evaluation, hosting recovery, provider quality or user benefit is inferred.


## 2026-11-26 - Christophe (C-29/C-30 evidence reconciliation)

**Did:** Synced #153 with main 4722838, preserving both shared handoff histories.
Updated owned architecture/provenance/memory docs, web README and report draft for
merged Calendar/Gmail APIs and controls, the published chatbot result and the last
verified Azure candidate 6749fb0. Removed #153's obsolete role-guide addendum so
the separate #170 turnover redesign owns that document. No backend implementation
or contract was read or changed; no deployment, membership or credential change.

**Grading:** Prepared web/GRADING_GUIDE.md against the original brief's pages 5-6:
seven suggested weights, existing evidence, free reproduction commands and gaps.
The engineering bonus rewards demonstrated practice/impact; the brief does not
require a fixed number of meetings. C-31 still needs its own team evidence review.
C-30 is doing against existing interfaces, not complete: T-27/C-22/C-29 acceptance
and an actual fresh independent review remain open. No new runtime design/failure
was introduced, so no new D/F identifier was needed.

**Verified:** Required root gates pass on the synced source: Ruff/format 187 files,
mypy 92, schema/task validation, 949 tests and 93.76% coverage. The reused locked
environment's uv.lock matches. All 104 local targets/anchors in seven edited guides
resolve; four web Markdown files pass Prettier. The guide's free replay export
produces two synthetic cases, zero errors and seven expected columns with both
ratings blank. No private data or paid provider call. PR-head CI is separate.

**Next / owners:** Tatiana: review/incorporate the linked report sections into T-27
and link the guide from the root README; reconcile docs/evidence.md and
docs/rubric-map.md, which are outside Christophe's folders. Joey: retry the actual
README-only setup when Docker works. C-39 #170 is green but remains a synthetic
prototype until Tatiana supplies #169's atomic term/cabinet/session contract.
Signed-in phone/provider acceptance, backup restoration, production telemetry and
final held-out thresholds remain unverified. Preserve commits and independent
review under current AGENTS; historical waivers do not prove reviews happened.

**Task reconciliation:** C-38 now reads done after verifying #166's actual merge
e884039. Its scoped UI checks/captures were already recorded; this correction
does not claim a missing independent review or signed-in provider acceptance.

## 2026-11-27 - Christophe (C-29/C-30 sync after #168)

**Did:** Merged main b3ce74e after #168. Resolved the handoff conflict by
retaining every complete branch section and every main deployment/verification
section; checked that no section heading from either side was lost. Existing
task statuses and dated receipts are retained. No backend contract, host setting
or live provider operation changed as part of this merge.

**Verified:** Required root gates pass: Ruff/format 187 files, mypy 92, schemas
and task validation; 949 Python tests, 93.76% coverage. Full web quality/build
checks pass (151 units and 42 board-tool tests), lint/format, rehearsal types
and production build. Matching locked dependencies used. Current-head GitHub CI
will run after this sync is pushed; prior green checks are historical.

**Next:** Independent owner review and merge commit after all fresh checks pass.
Chris requests a verified current-main redeploy whenever this assistant merges
to main; that operational step is separate from syncing a PR branch. Calendar
Connect remains under C-18/C-35 diagnosis: saved 26 November host comparisons
match the supplied ID/redirect, but current Google-console values and the
callback's exact failure stage are not yet established. Owner handoff is #83.
