# Handoff log — Calendar, reminders, draft templates

Owner: Joey Saade. Tasks in `TASKS.md`; protocol in `AGENTS.md`. See `docs/handoff/TEMPLATE.md` for the entry format. Append new entries at the bottom.

No entries yet.

## 2026-10-23 — Joey, with Codex (feat/joey-calendar-drafts)

**Did:** Built approved-plan calendar items, a Google Calendar HTTP adapter, stable one-way sync, role-specific reminder events, completion/cancellation handling, and club-wide reminder builders. Added a WhatsApp writer that drafts an announcement and reminder using only approved examples from the current club and verified event facts. Added fake-Google and synthetic model tests, failure rows F-76 to F-79, decisions D-61 and D-62, and setup notes.

**State:** Root lint, formatting, strict types, 242 tests, schema drift and task validation pass locally. The branch is based on Christophe's web branch because PR #9 is not merged yet. No live Google call or real club message was used. J-01 is blocked on OAuth setup, calendar IDs and a cabinet-approved test; J-07 still needs the non-WhatsApp templates and cabinet feedback.

**Next:** Connect the backend approval and role directory in T-22 to `event_items` and `CalendarSync`, with a persisted retry queue and sync status; then perform a live test when Joey provides calendar IDs and OAuth credentials privately.

**Open questions / blockers:** Google reminder subscriptions need a private role calendar for each role and must be maintained when role holders change. The impact-form example in `docs/calendar-contract.md` combines a due date two days after the event with `after_days` 2 and 5; the implementation schedules notifications at two and five days after the event and should be reconciled with Tatiana before changing the shared contract. Approved historical WhatsApp examples will be provided later and must remain outside git.

## 2026-10-23 — Joey, publication update (PR #15)

**Did:** Pushed commit `8f072c6` and opened draft [PR #15](https://github.com/Nohra2005/ClubOps/pull/15) against Christophe's web branch, which is still pending as PR #9.

**State:** Branch published; local checks passed. PR #15 is draft so the stacked dependency and live setup gaps remain visible.

**Next:** Get the shared calendar and private role calendar IDs, OAuth client and private approved message examples; then run a cabinet-approved live calendar test and draft review.

**Open questions / blockers:** J-01 remains blocked on live Google setup. T-22 must connect approval and retry persistence. Non-WhatsApp J-07 templates are still to do.

## 2026-10-31 — J-06 calendar queue connection cleanup

**Did:** Explicitly closed SQLite connections after queue setup, enqueue, reads, retry errors, and successful drains. Focused calendar tests pass with warnings treated as errors.

**State:** Fake-Google coverage remains green. J-06 still needs the full failure suite and owner-side deployed integration before completion.

## 2026-10-23 — Joey, retry-queue follow-up (PR #15)

**Did:** Added a SQLite queue for approved calendar items. A Google outage leaves the latest version pending across a restart; a later drain retries it and clears it after successful sync.

**State:** Fake-Google tests cover the outage, restart and replacement with a moved date. Backend scheduling and UI sync status still need T-22.

**Next:** Have T-22 call queue enqueue only after revision-bound plan approval, then drain on the server schedule.

**Open questions / blockers:** Live Google setup and private message examples are pending Joey's account data.

## 2026-10-31 — J-14 synthetic event set

**Did:** Added ten synthetic event types in `eval/synthetic-events.csv`, with approval labels based on the checked-in AUB rulebook. Used the columns consumed by the existing D5 evaluation loader.

**State:** J-14 is ready for Tatiana's label review. The private Running Club CSV header is unavailable in this checkout, so exact header parity needs her confirmation before T-38 freezes the set. No real club information was added.

**Next:** Confirm the labels and header with Tatiana; then freeze the dataset in T-38. Continue Joey's J-12 proposal drafter in a separate task PR.

**Open questions / blockers:** The road-trip safety label and the interpretation of a film screening without filming should be explicitly checked by Tatiana. The current schema drift check reports an out-of-date `docs/capabilities.md` unrelated to this CSV change.

**PR update:** Draft PR #33 is open for J-14. The trip case now explicitly involves challenging hiking so the safety label has a stated trigger. Tatiana's header and label review remain the acceptance gate.

## 2026-10-31 — J-12 proposal draft, first implementation

**Did:** Added a deterministic proposal drafter for the versioned form contract. It maps confirmed event, club and requester values, uses 24-hour times, records origins, and leaves unknown answers and files for a person. Synthetic tests cover the current form and an extra conditional field.

**State:** Focused tests, Ruff and mypy pass. The task remains doing: the official materials extension is absent from the checked-in form template, and Tatiana still needs to wire the capability into the agent and page.

**Next:** Check the official materials questions with the form owner, then test the complete 39-question template and add agent integration through Tatiana's API PR.

**Open questions / blockers:** Do not invent wording or choices for the missing official form questions. Repository-wide schema drift remains in `docs/capabilities.md` and needs its owner to resolve it.

## 2026-10-31 — J-12 official conditional form follow-up

**Did:** Merged the official form update from main (q34–q52) and replaced the provisional conditional-field test with tests against that form. The drafter includes all fields, leaves unsupported materials and catering details visibly unknown, and keeps confirmed dates and 24-hour times.

**State:** The form wording is now available. Agent and event-page integration remain Tatiana-owned. Repository-wide schema drift in `docs/capabilities.md` remains with its owner.

**Next:** Tatiana wires the draft tool through the agent and event API, then checks the rendered draft and its pending fields with the form owner.

## 2026-10-31 — J-15 cited chatbot core

**Did:** Added a chat service that searches approved current facts in the requester's club, redacts the question, calls the model with a one-step budget, checks citations against retrieved fact IDs, and returns an explicit unknown answer when evidence is unavailable or invalid. Synthetic tests cover a known answer, cross-club isolation, invalid citations and redaction.

**State:** Core is ready for Tatiana to wire to `/api/chat/ask`. The task remains doing until app integration and the private 42-question evaluation are recorded. No real questions or club data entered the repository.

**Next:** Coordinate API wiring with Tatiana, run the private set, and adjust only based on documented failure cases.

**Open questions / blockers:** The GitHub connector could not create PRs for this repository (404); branches can be pushed but reviews still need the connected GitHub access restored.

**PR update:** Draft PR #35 is open through the authenticated GitHub API. Added tests for stale facts, model uncertainty and the one-step budget; 394 tests pass. Tatiana's API wiring and private evaluation remain.

## 2026-10-31 — J-17 chatbot evaluation runner

**Did:** Added a scorer and CLI that read a redacted question CSV, use approved knowledge and the rulebook, call the cited chatbot through the model client in replay mode, and report correctness, invented answers, correct unknowns, unsupported citations and estimated cost. Synthetic tests include a CLI replay run without credentials.

**State:** The synthetic test passes. This branch is stacked on J-15 because the runner calls its chat service. Private frozen CSV header and recordings need Tatiana's verification before J-17 can be marked done.

**Next:** Align the private column mapping and evaluate the frozen set after J-15 is integrated.

**Open questions / blockers:** The private CSV and model recordings are intentionally unavailable in this checkout; no private question text should enter git.

## 2026-10-31 — J-07 remaining draft types

**Did:** Added model-backed templates for sponsor email, Instagram caption, poster text, expense form, volunteer shifts and impact report. The existing WhatsApp announcement and reminder remain in place. Synthetic tests cover every new type, club-specific approved examples, redaction, unsent state, wrong event and unsupplied citations.

**State:** Local tests pass. J-07 remains doing until approved private club examples and J-08 cabinet feedback establish that the drafts are usable without edits.

**Next:** Review drafts for three past events with two cabinet members, then revise templates from their feedback.

**Open questions / blockers:** Real style examples must remain in private data and not be added to tests, prompts committed to git, or traces.

## 2026-10-31 — J-10 Gmail intake core

**Did:** Added a Gmail read adapter and private SQLite queue for forwarded mail. It accepts exactly one known club tag and a sender on that club's cabinet list, deduplicates by Gmail message ID, and wraps mail content as `Untrusted`. Attachments are represented by name only. Synthetic tests cover routing, outsiders, duplicates, pagination and embedded instructions. Recorded D-77 and F-118 to F-121.

**State:** Polling performs no AI call and does not auto-approve. J-10 remains doing until Tatiana's human-click Review integration and a cabinet-approved live forward after T-39 access.

**Next:** Wire pending requests to a cabinet action that calls `Learner.learn`, then mark the queue entry processed after Review cards are saved.

**Open questions / blockers:** T-39 account access and owner-side API integration are pending. The task text's automatic mail-to-Review wording conflicts with the project-wide AI-on-click rule; D-77 records the safe interaction.

## 2026-10-31 — J-10 forwarding address correction

**Did:** Matched the routing parser and synthetic fixtures to the designated `clubops.agent+<club>@gmail.com` address. Closed private SQLite connections after use.

**State:** Synthetic intake is ready for owner-side Review wiring; delegate access alone has not yet supplied a live Gmail API token or acceptance forward.
## 2026-10-31 — J-11 daily check core

**Did:** Added plain-code findings for overdue tasks, deadlines within two days and plans outdated by edits. Added an official-page hash comparison that treats the first successful fetch as a baseline and later changes as human-review findings. Synthetic tests cover these cases and done/cancelled work. F-122 and F-123 record the failure modes.

**State:** The task remains doing. The server scheduler, official OSA fetch, hash persistence and Calendar/Review reminder writes are owner-side integration work. No scheduled AI call was added because the project only allows AI after a person's click.

**Next:** Coordinate deployment scheduling and API persistence with Christophe and Tatiana; verify the resulting reminders on the deployed app.

**Open questions / blockers:** A failed source fetch must surface a warning rather than an unchanged-page claim; add this in the scheduler integration.
## 2026-10-31 — J-13 adversarial boundary suite

**Did:** Added synthetic security tests for forged sign-in, adviser approval, cross-club access, injected email and event text, unverified fake rules, and step/cost limits. Updated the threat model to distinguish these regression checks from a measured attack success rate.

**State:** The new tests pass. J-13 remains doing because the broader frozen attack corpus, defense-off/on model run, result table and report sections are not complete.

**Next:** Expand the corpus after J-15 chat and J-10 inbox integration, then run and record both configurations with Tatiana.

**Open questions / blockers:** Results belong in Tatiana's `results/` area; coordinate the measured run and evidence before poster claims.

## 2026-11-10 — J-12 form-version regression (test/j12-form-versions)

**Did:** Added synthetic checks for the historical 33-field shape selected by field ID from the current form, plus the current 52-field catering branch. The legacy draft validates with its known values; the current conditional fields remain explicitly pending when the event lacks facts.

**State:** Focused proposal tests pass. J-12 remains doing because official required fields need human confirmation and Tatiana owns agent/event API wiring in issue #83. No contract or form source was changed.

**Next:** Tatiana should wire the existing drafter through the published draft contract; Joey should verify a cabinet-reviewed complete proposal and adjust only sourced fields.

**Open questions / blockers:** The synthetic 33-field shape is a compatibility test, not a newly sourced historical OSA form. Keep real submitted proposals private.
## 2026-11-10 — J-19 proposal accuracy runner

**Did:** Added a deterministic runner that builds drafts from versioned proposal requests, checks them against the form and verified per-field truth, and outputs only category counts and safe case IDs. Synthetic tests cover category boundaries, incomplete truth rejection and a CLI replay. Recorded D-108 and F-199.

**State:** J-19's synthetic acceptance check is met on pushed branch `eval/j19-proposal-accuracy`; PR and teammate review remain. Full pytest passes (602 passed, 1 skipped; 92.72% coverage), as do Ruff and mypy. The pre-existing `docs/capabilities.md` schema drift still prevents the full check gate. The private submitted proposals remain with Tatiana for T-26. No private form answer was committed or printed by the runner.

**Next:** Tatiana maps each private proposal to a versioned request and complete truth map, then runs `uv run python scripts/eval_proposals.py --cases <private-json> --out <private-result>` during T-26.

**Open questions / blockers:** Real historical proposals may need field-by-field transcription before scoring; this is evaluation data work, not a reason to invent missing truth.

## 2026-11-10 — J-19 review request

**Did:** Opened PR #80 from `eval/j19-proposal-accuracy` into `main` and requested Tatiana's review. The PR body records the private-data boundary and T-26 handoff.

**State:** J-19 is in review. CI and teammate approval remain before merge.

**Next:** Address review findings and keep the runner's output free of proposal answer text.

**Open questions / blockers:** The shared `docs/capabilities.md` schema drift still blocks the local full check gate and needs its owner to resolve.
## 2026-11-10 — J-21 shared-calendar cabinet access

**Did:** Added a Google Calendar ACL adapter that grants named cabinet members reader access and revokes only their reader rule. It is safe to repeat and preserves manually elevated roles. Added synthetic tests, D-110 and F-198. The user confirmed the ClubOps account, Cloud APIs, OAuth sign-in client and Running Club shared calendar exist, but supplied no calendar ID or tokens.

**State:** Branch `feat/j21-calendar-sharing` was committed and pushed. Adapter tests and full pytest suite pass (602 passed, 1 skipped); Ruff and mypy pass. The repository's existing `docs/capabilities.md` schema drift prevents the `make check` equivalent from passing, and `make` is not installed on this machine. No live Google operation was made. The connected GitHub PR creation endpoint returned 404; open the PR from the pushed branch.

**Next:** Tatiana adds server-side Calendar OAuth with `calendar.events` and `calendar.acls`, private token refresh and retryable cabinet add/remove triggers. Christophe connects Settings to real connection and sharing status. Then run a cabinet-approved live test and mark J-21 done.

**Open questions / blockers:** Calendar ID must be supplied privately. Google does not guarantee that ACL sharing automatically adds the calendar to each member's sidebar. Current role-specific reminder calendars remain a separate integration decision; the shared-calendar reader adapter does not implement them.

## 2026-11-10 — Google integration owner handoff

**Did:** Recorded T-46 for Tatiana's Calendar OAuth, sync and cabinet sharing triggers; T-47 for her Gmail OAuth and human-click Review path; and C-35 for Christophe's Settings and inbox UI. Updated J-01's blocker to reflect the Google setup the user completed. These task descriptions are the team handoff; no private credential or calendar ID was added to the repo.

**State:** Joey still needs the Running Club calendar ID stored privately, owner-side OAuth routes, a cabinet-approved live Calendar and mail test, approved style examples, and J-08 cabinet feedback. The Google ACL adapter is ready for T-46 integration, but J-21 is not complete until the live test.

**Next:** Continue J-19's synthetic proposal accuracy runner while the Google owner tasks proceed.

**Open questions / blockers:** The existing calendar contract uses private role calendars for reminders; the user has deferred creating those. Tatiana and Joey must agree on any contract change before claiming role-specific Google reminders work.

## 2026-11-10 — J-21 review request

**Did:** Opened PR #79 from `feat/j21-calendar-sharing` into `main` and requested Tatiana and Christophe as reviewers. The PR body points to T-46, T-47 and C-35 as owner-specific follow-up work.

**State:** J-21 is in review. The adapter has synthetic coverage; the live Google test needs Tatiana's OAuth integration and the private Running Club calendar ID.

**Next:** Address review comments, then run the cabinet-approved local test once the owner-side API is connected.

**Open questions / blockers:** CI still has the shared schema drift on `docs/capabilities.md`; no real Calendar access rule has been changed.

## 2026-11-10 — J-01 manual Google setup confirmed

**Did:** Recorded the user's completed Google setup in J-01 and added a placeholder for `CLUBOPS_GOOGLE_RUNNING_CLUB_CALENDAR_ID` to `.env.example`. The real value remains only in the user's ignored local `.env`.

**State:** J-01 remains blocked at its live-test acceptance gate. T-46, T-47 and C-35 still need owner-side authorization and UI flows; no live Calendar or Gmail permission was granted by this documentation change.

**Next:** Work on J-20 with synthetic clubs and replay mode while owner integrations proceed.

**Open questions / blockers:** The user does not require manual Calendar sharing. The private role-calendar reminder architecture remains an explicit contract decision for Tatiana and Joey before live reminders are claimed.


## 2026-11-11 - J-21 per-club Calendar configuration (PR #79)

**Did:** Merged current main and answered Tatiana's review with a private JSON map keyed by club slug. Added a parser and synthetic tests for two clubs, malformed/duplicate entries and generic errors; changed `.env.example` to a blank map setting. Recorded D-120 and F-205.

**State:** Joey's existing local Running Club ID remains private but must be moved from the old single-club variable into `CLUBOPS_GOOGLE_CALENDAR_IDS_JSON` on his machine. T-46 still must load the map and implement OAuth, sync and cabinet triggers; C-35 still owns UI status. No live access test has run.

**Next:** Tatiana reviews the map format and wires it in T-46; Christophe reviews Settings expectations. After both land, Joey performs a cabinet-approved multi-club isolation and reader-access test.

**Open questions / blockers:** PR #90 proposes a one-calendar-per-club reminder decision. Coordinate any change to the calendar contract with Tatiana before changing Joey's role-reminder behavior.
## 2026-11-10 — J-16 and Joey integration audit (docs/j16-owner-handoffs)

**Did:** Audited J-02–J-06, J-12 and J-17 against synthetic acceptance tests. The focused calendar, proposal and chat tests pass. Recorded the current 52-field proposal template and corrected the stale 33-field progress note. Published repo issues #83 (Tatiana) and #84 (Christophe) with concrete Google, Gmail, API, evaluation, scheduling, deployment and CI handoffs. J-16 is blocked on CI workflow ownership because `.github/workflows/` is outside Joey's assigned folders.

**State:** No teammate-owned code or private content changed. The fake-Google/calendar queue, proposal drafter and chat runner are testable; live Google/Gmail, private evaluations, complete proposal acceptance and the deployed scheduler are still open. J-20 draft PR #81 has no legitimate model recordings yet. PRs #79/#80 need independent review.

**Next:** Christophe should identify the CI owner in #84 and implement pinned gitleaks/Bandit gates; Tatiana should specify integration fields and private evaluation inputs in #83. Joey then runs the live calendar/mail acceptance and cabinet draft review after those prerequisites land.

**Open questions / blockers:** The existing Windows schema check reports `docs/capabilities.md` drift, while GitHub CI is green. Keep all calendar IDs, tokens, club examples and feedback out of Git.

## 2026-11-12 - J-22 pre-read inbox guards

**Did:** Added a private SQLite verification/read ledger and synthetic pre-paid-read guards in Joey's inbox folder. A member's extra sender address needs a salted six-digit code mailed to the club plus-address within ten minutes; five wrong attempts lock it, and removal revokes it. A forward needs a matching club tag, authorized forwarder and operator-supplied OSA original sender. Cleaned text remains untrusted. Global original-message fingerprints skip a read already completed for another club. Added D-123 and F-209 to F-213 with regression tests.

**State:** Synthetic guard tests pass; no Google call, model call, real address or club content is in this PR. J-22 is in review. The existing Gmail fetch/queue path remains separate, and T-47 API integration/live acceptance has not happened.

**Next:** Tatiana should call the guard from the human-click capture route, derive authorized senders from the cabinet plus verified entries, pass the private OSA list, claim the fingerprint before the paid call, save Review proposals, then mark it read. Release the claim on failure to keep the mail retryable and show the skip reason through C-35. Please resolve PR #92's explicit-role allowlist review first. Christophe should use T-47's published response/error shapes for the C-35 screens.

**Open questions / blockers:** A live forward and cross-club read-once check need T-47 and cabinet approval. The claim expires after ten minutes so a crashed read can be retried; T-47 must handle that retry and avoid claiming before a person clicks. Do not commit the OSA sender list or codes.

## 2026-11-16 - Joey: J-22 Outlook review and task acceptance audit

**Did:** Pulled the current branch, fetched and merged main 54d38c1, preserving both failure-matrix histories. Addressed Tatiana's PR #93 blocker: recognize Outlook underscore forwards, accept and discard Sent/To/Cc, retain Gmail/Date handling. A synthetic Outlook test checks clean content, non-OSA rejection and cross-club duplicate rejection. Marked J-17/J-19 done against their explicit synthetic runner gates; private T-26 scores are still pending.

**State:** J-22 remains review pending current-head independent approval and CI. #79/#80/#85/#86 are already merged; this session does not claim those merges. No private mailbox data or paid calls were used.

**Next:** Tatiana re-reviews #93 and wires guards into T-47 (#95), including claim/release and skip reasons; Christophe uses those shapes in C-35 (#94).

**Open questions / blockers:** J-23 requires a coordinated CalendarItem contract extension for deadline approval and per-event invitees; T-48 (#96) alone does not provide that contract. J-13/#82 needs actual defense-off/on outcomes; J-20/#81 needs real model replay recordings. J-16 still needs CI-owner work in #84; calendar/Gmail acceptance, cabinet draft feedback and poster numbers remain external gates.

## 2026-11-16 - Joey: verified acceptance and team review handback

**Did:** Reviewed all 12 open PRs' metadata, discussions, review states and CI; inspected the relevant inbox/restore/calendar changes. Reviewed and merged #88 with a merge commit (7109e06). Approved #92's explicit-role fix, requested changes on #95 (paid reads bypass J-22) and #96 (shared-fact Restore bypass). Sent concrete handoffs in #83/#84. Synced #81 and #82 separately with main, preserving both logs; they remain draft pending legitimate measured outcomes.

**State:** #93 code passes the full 686-test suite (one skipped), 92.79% coverage, Ruff/format, mypy, schemas and task checks. GNU Make is absent; its equivalent commands ran. J-02/J-05/J-06 meet their fake-Google test gates, J-14 has Tatiana-reviewed frozen labels, and J-17/J-19 have synthetic replay runners. These status corrections do not imply live calendar, private model evaluation or send-ready cabinet acceptance. J-03/J-04 remain doing for reminder acceptance and the D-116 integration decision.

**Next:** Tatiana and Christophe re-review #93, integrate its guard before exposing #95 paid capture, and publish the separate deadline/audience contract for J-23. PR #92 still needs its shared main conflict resolved by its owner before merge.

**Open questions / blockers:** Calendar/Gmail live acceptance and deployed sync require T-46/T-47/C-35; J-07/J-08 need approved private style examples and two cabinet reviewers on three events; J-11 needs server scheduling/persistence; J-12 needs official-form/app acceptance; J-13 needs detector fix and measured on/off outcomes; J-15 needs private chatbot evaluation; J-16 needs CI-path ownership and gates; J-18 awaits T-26 results and Tatiana's number check; J-20 needs matching legitimate replay recordings; J-21 needs cabinet access integration/live acceptance; J-23 needs the coordinated contract. Fresh README-only setup requested by C-29/#99 is still unverified. No invented evidence, private data or paid model calls were used.

## 2026-11-16 - Joey: final PR handoff update

**Did:** Resolved #92's main conflicts in shared design/failure logs only, preserving both sides; pushed e5038a9 to Tatiana's existing branch and independently re-approved the exact-role fix. Sixteen focused Gmail/intake/task tests and lint/format/types/schema/task checks pass. This supersedes the earlier request that its owner resolve the conflict. Updated #81's description to the actual 15-row interview-first pipeline and posted current-head review handoffs on #81/#82/#93 and issues #83/#84.

**State:** #88 merged as 7109e06; #92 is synchronized and approved, waiting for current-head CI; #93 has the Outlook fix and six verified task-status corrections, waiting for teammate re-review and current CI. #81/#82 stay draft for missing measurements. All local work is committed/pushed; the original Joey branch remains checked out.

**Next:** Merge #92 with a merge commit after all required checks succeed, and #93 after independent approval plus CI. T3 PR watches will handle those external waits.

**Open questions / blockers:** #95 and #96 have actionable changes-requested reviews; #91/#94/#99 lack current independent approval and/or remain draft. No unreviewed or incomplete PR was merged.

## 2026-11-16 - Joey: J-22 watch recovery and merged Gmail-fetch sync

**Did:** Checked #93 directly after the host watch failed. Tatiana approved the Outlook fix; all five checks on the previous head passed. Main now includes #92. Merged it into #93 and resolved only the shared failure-matrix conflict, preserving F-207/F-208 and all J-22 rows. No inbox guard or Gmail-fetch behavior changed.

**State:** Current-head checks and independent re-review must be assessed after this merge-only update; #92 is already merged, superseding the previous waiting state.

**Next:** Restart the #93 watch after pushing; merge only with current approval and green required checks.

**Open questions / blockers:** T-47 paid-read integration remains in #95. Host watcher access is unreliable; the direct authenticated GitHub API remains readable.

## 2026-11-20 - Joey: complete task and owner-handoff audit

**Did:** Pulled current main, reconciled #81/#82 preserving shared histories, completed J-13 report sections, and reran focused/full checks. Reviewed and merged #96 as 0ac0b5b after seven archive tests and all five CI checks passed. Re-reviewed #95: 15 focused inbox tests pass and the earlier J-22 bypass is fixed. Approval is posted; merge failed because #96 creates documentation conflicts. Aborted the local merge cleanly rather than edit owner-maintained docs/api.md. Updated J-04/J-12/J-22 to done at their explicit synthetic gates and made remaining external blockers concrete. Added live Calendar and cabinet draft-review receipt procedures in owned READMEs.

**State:** #81 head c9070fd: five tests and 15 checklist rows, no measured model curve. #82 head 797a3c3: 696 passed, 1 skipped, 1 strict expected failure, 92.77% coverage; lint/format/types/schemas/tasks passed. Those PRs remain draft for their documented evidence gates. This audit PR is documentation/status work, not live acceptance. No secret, private data, dependency or production setting changed.

**Next:** Tatiana reconciles #95 with #96 and requests current-head review, fixes F-204, supplies legitimate recordings/private evaluation, and coordinates T-46/J-23 contracts with Joey. Christophe reviews the audit and finishes C-35/deployment integration against the published owner responses. Joey then runs approved live/cabinet acceptance when those prerequisites exist.

**Open questions / blockers:** T-46 OAuth/worker/cabinet triggers, J-23 contract, J-10 live forward/proof/removal, scheduled durable J-11, two cabinet reviewers and private style examples, private chatbot/new-club/security evaluation, J-16 workflow ownership/gates, and T-26 poster numbers remain external gates. Docker Linux engine is unavailable, so README-only fresh startup is blocked before Compose. Email connectors are unconnected; team notification uses explicit GitHub mentions/review requests. The earlier repeating #92/#93 watches monitored already merged PRs and should be stopped.

**Audit validation:** On main plus merged #96, the complete pytest/coverage gate passed with one skipped test and 92.80% coverage. Ruff lint/format, strict mypy, schemas, task validation and diff checks passed. GNU Make is absent, so its listed equivalent commands ran. No new application behavior or design decision is introduced by the audit status/receipt documentation.

**Published review handoff:** Audit PR #102 is open. After #96 merged, #81 was reconciled again to ae922e3 and #82 to 84a08e7, preserving all shared rows; #81's five tests pass and #82's shared-log/security checks pass with F-204 still expected-failing. The initial focused command named a nonexistent test file; it was corrected to the repository's actual task/log/failure test paths and passed. Docker Desktop was started locally; its engine version API returned HTTP 500, so fresh Compose acceptance remains unverified. No production service was started.


## 2026-11-21 - Joey: coordination, independent reviews and email workflow (J-24)

**Did:** Fetched current main and inspected open/recent PRs, reviews, CI, issues #43/#83/#84 and owner handoffs. Verified #95/#94/#102 landed in main before this pass. Re-reviewed #103's pending-mail audience backfill: 93 focused tests pass; approved e5392e3. Reviewed/approved #100, #101, #91, #99 and the narrow #97/#98 lock updates. Merged #100 as c53948f, #97 as 72640d9 and #98 as 60d7027 with merge commits. These are verified GitHub merge responses, not promises to merge. Requested Christophe's owner review on #104. Sent specific owner PR/sync requests in #83/#84; no finished unsubmitted feature was assumed to exist.

**State:** #91/#99/#101 have approvals but conflict after main changed. A trial #101 merge identified shared design/failure logs plus Christophe-owned docs/handoff/web.md and web/VERIFICATION.md; aborted cleanly without editing those files. #99 merge returned 405 conflicts. #103 also needs Tatiana's main sync, preserving merged Inbox/frontend and handoff evidence; #104 awaits Christophe and its dependency/base handling. #81/#82 remain drafts for genuine missing measurements. T-48 is corrected to done at the merged #96 synthetic gate; J-10 now names merged #95/#94 while retaining its live proof/removal/Review gates. No deployment, private acceptance or model evaluation was performed.

**Verification:** Board tooling: 32 Node tests pass. Development lock audit: zero vulnerabilities; existing production lock entries unchanged. Local Vitest could not run because node_modules/Vitest is absent; current-head CI supplied the web unit/browser gates and this review installed no packages. Python inbox/learning review: 93 pass. The complete local check result is recorded below after completion; no local installation of the bot dependency updates is claimed.

**Email:** Gmail and Outlook were confirmed unconnected. Both teammate addresses were verified from their Git author history; ready-to-send drafts stay in ignored data/private/coordination-2026-11-21/, never in Git. No project email thread could be read, duplicates checked by email, or email sent. GitHub comments are actual notifications, not email delivery. AGENTS.md now specifies the user's project-coordination email triggers, verified recipients, thread/deduplication rules and honest draft fallback; this does not change the application's human-approval boundary.

**Next:** Tatiana and Christophe review the J-24 instructions/status PR. Christophe synchronizes #91/#99/#101, obtains fresh review/green CI and reviews #104. Tatiana synchronizes #103 and links or opens the missing T-06 review PR if ready; requests for any finished unpublished integration work are in #83/#84. Do not mark C-13/C-29/C-31 or real integrations complete merely because their bounded PRs are approved/merged. Team email drafts need connected email access before sending.

### Active-task reconciliation at this pass

TASKS.md remains authoritative. "No open PR" means no matching current open PR was found, not that the task is abandoned. Dependencies remain explicit; no private results or meetings are inferred. Next actions below belong to the named owner unless another owner is stated.

| Task | Owner | Status | PR / dependency | Next action |
|---|---|---|---|---|
| T-06 | tatiana | review | No open PR | Link existing review or open baseline PR if ready (#83). |
| T-09 | tatiana | doing | T-18 merged | Finish private seed review; record counts privately. |
| T-26 | tatiana | todo | T-44, J-13/J-15/J-20 | Collect legitimate private runs and final evidence at freeze. |
| T-27 | tatiana | todo | #99 / #104 | Incorporate reviewed report sections and measured results. |
| T-28 | tatiana | doing | #43 / #83 / #84 | Coordinate owner syncs and record real team decisions. |
| T-29 | tatiana | todo | T-26 | Back poster/report claims with actual evidence files. |
| T-32 | tatiana | todo | No open PR | Run the approved real pilot and retain private evidence. |
| T-33 | tatiana | doing | No open PR | Complete consented handover sessions and actual observations. |
| T-39 | tatiana | doing | #92/#95 merged | Finish private account/access prerequisites and live mail acceptance. |
| T-40 | tatiana | doing | Reviewed merge history | Confirm available branch protections; retain genuine approvals. |
| T-44 | tatiana | todo | J-20 / #81 | Finish private ASME onboarding and leak-check evidence. |
| T-46 | tatiana | todo | No open PR / #83 | Publish scoped OAuth/worker/ACL integration PR if ready; otherwise state blocker. |
| T-47 | tatiana | doing | #95/#94 merged; #103 open | Finish proof/removal and real forward-to-Review acceptance. |
| C-13 | christophe | doing | #100 merged | Complete deployed Google/every-screen acceptance. |
| C-14 | christophe | todo | C-18 | Supply hosted frontend acceptance after authorized deployment. |
| C-15 | christophe | todo | C-28 | Finish actual demo support and disclose synthetic evidence. |
| C-18 | christophe | doing | #84 | Finish host/Google/persistent storage setup; deployment still needs authorization. |
| C-20 | christophe | doing | T-26 | Integrate known-club provider metadata and real report evidence. |
| C-21 | christophe | doing | #55/#87 merged; #99 | Finish genuine new-club acceptance beyond synthetic setup tests. |
| C-22 | christophe | todo | T-26 / #84 | Link/open evaluation CI PR if ready; keep results replay-only in CI. |
| C-25 | christophe | doing | Local exporter evidence | Finish actual producer hooks/hosted evidence before claiming live traces. |
| C-26 | christophe | todo | C-18 | Supply deployed monitoring/alert evidence after hosting. |
| C-28 | christophe | doing | Synthetic rehearsal | Finish actual demo/backup recording and final measured narrative. |
| C-29 | christophe | doing | #99 approved, conflicts | Sync owner docs, re-review, then complete fresh README setup/report incorporation. |
| C-30 | christophe | todo | T-27, C-29 | Update grading links to final real evidence. |
| C-31 | christophe | blocked | #91 approved, conflicts | Sync/re-review; record three genuine weekly reviews. |
| C-33 | christophe | doing | Merged starter UI | Finish actual ASME onboarding acceptance; retain browser-local checklist limits. |
| C-35 | christophe | doing | #94 merged; T-46/T-47 | Complete forwarding proof/settings and agreed deadline/audience UI contracts. |
| J-01 | joey | blocked | T-46 | Run cabinet-approved live Google setup acceptance after OAuth integration. |
| J-03 | joey | blocked | T-46, J-23 | Validate live approved reminders/audience with durable worker. |
| J-07 | joey | blocked | Private approved style examples | Obtain consented examples and complete cabinet template acceptance. |
| J-08 | joey | blocked | J-07 | Collect two cabinet reviews on three consented events; apply/recheck edits. |
| J-09 | joey | blocked | C-18, T-46 | Run approved deployed sync/retry/restart receipt. |
| J-10 | joey | blocked | #95/#94 merged; #103 | After Tatiana proof/removal work, run approved skip/retry/read-once Review receipt. |
| J-11 | joey | blocked | #84 scheduler/storage | Obtain durable scheduled checks and restart evidence. |
| J-13 | joey | blocked | #82 draft; F-204 | Tatiana resolves detector behavior; obtain reviewed attack/benign on/off outcomes. |
| J-15 | joey | blocked | API wiring/private questions | Confirm app integration and run private 42-question evaluation. |
| J-16 | joey | blocked | #83/#84 workflow ownership | Tatiana assigns workflow paths; implement pinned scanning only after ownership agreement. |
| J-18 | joey | blocked | T-26/T-27 | Use final evidence files and Tatiana-checked poster numbers. |
| J-20 | joey | blocked | #81 draft; T-44 | Obtain legitimate matching model recordings and measured replay curve. |
| J-21 | joey | blocked | #79 merged; T-46 | Run cabinet-approved reader ACL add/remove acceptance. |
| J-23 | joey | blocked | Tatiana / #83 | Agree standalone versioned deadline/named-audience contract before implementation. |
| J-24 | joey | review | Instructions/status PR | Obtain independent review; distinguish actual merges/emails from pending work/drafts. |
| T-49 | tatiana | review (open PR) | #103 approved, conflicts | Sync main, obtain fresh CI/review, then perform the free pending-mail refresh. |
| C-36 | christophe | review (open PR) | #101 approved, conflicts | Sync owner docs, obtain fresh CI/review, then merge the development-tool fix. |

**J-24 final local validation:** GNU Make is absent; ran the equivalent Ruff lint/format, mypy (85 source files), schema export check, task check and pytest/coverage using `uv run --no-sync` in the existing environment. All passed: 709 tests, 1 skipped, 92.85% coverage. The bot lock updates were merged without installing them locally; their exact-head GitHub CI passed before merge, and fresh-lock CI on this PR remains required. `git diff --check` passes. Only AGENTS.md, TASKS.md and this additive handoff change. No application behavior, contract, new failure mode or secret changed.
