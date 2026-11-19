# ClubOps tasks

The single list of who does what until the demo on **30 November 2026**.

- **See your own list:** `make tasks WHO=tatiana` (or `christophe`, `joey`). `make tasks` shows everyone.
- **Update it in the same PR as the work:** change `Status`, tick the checklist. Put `Task: T-14` in the PR description.
- **Stuck?** Set `Status: blocked` and write why under the task. Tell the owner of the task you wait on.
- **New task?** Add it at the end of the owner's section with the next free number. Never reuse or renumber an ID.
- `make check` fails if this file is malformed (unknown owner or status, a `Needs` ID that doesn't exist).

Status values: `todo` · `doing` · `blocked` · `review` (PR open) · `done`.

## How the work connects

- Christophe builds every screen against the **fake API data** in the UI spec, so he never waits for the backend. He switches to the real backend at C-13.
- Joey's calendar part reads the **calendar contract** (`docs/calendar-contract.md`). The backend sends calendar items only after a plan is approved.
- Tatiana's evaluation data (T-01 to T-04) is **frozen before** the planner (T-14) and chatbot (J-15) are built. Otherwise the test can be tuned to the system.
- The final test run (T-26) needs everything else done. Keep the last week for it.

Reference documents:
- UI spec (Christophe): https://claude.ai/artifact/XYRMvB5SZMxNSTv7jKvJam (Tatiana shares it)
- Calendar contract (Joey): `docs/calendar-contract.md`
- Decisions and reasons: `docs/design-log.md`
- Contracts (data shapes): `docs/contracts.md`, `src/clubops/contracts/`

---

## Tatiana: backend, agent, evaluation

### T-01 Correct the past-events table
- Owner: tatiana
- Status: done
- Needs: none
- What: Fill `approvals_real` for the 21 events in the private table (`clubops-raw/eval/d5-events.csv`). Answer the "?" rows first.
- Done when: every row has its real approvals; the 10 "?" questions are answered.
- Result (2026-10-22): 19 events kept (2 dropped), 27 facts learned, each tagged with its source event (`clubops-raw/eval/facts-learned.csv`). Two small open details: E10 (was the Neo coffee sponsored?), E19 (held in elections week?).

### T-02 Write the chatbot test (30 questions)
- Owner: tatiana
- Status: done
- Needs: none
- What: 30 questions a cabinet member would ask, each with the correct answer and its source. 10 of them must be ones ClubOps should answer "not sure, ask X".
- Done when: 30 rows saved privately, with answer, source, and who to ask for the "not sure" ones.
- Result (2026-10-22): `clubops-raw/eval/chatbot-questions.csv`, 30 questions, 10 "not sure".

### T-03 Write the learning test (10 facts)
- Owner: tatiana
- Status: done
- Needs: none
- What: 10 facts to teach ClubOps (by chat, after-event form or forwarded email) and, for each, a later question that should use it.
- Done when: 10 fact + question pairs saved privately.

### T-04 Freeze the test sets
- Owner: tatiana
- Status: done
- Needs: T-01, T-02, T-03, T-37
- What: Pick a random 30% held out (record the seed). Record the file hashes and date in `eval/FROZEN.md`. Other clubs' sets are frozen later in T-38.
- Done when: `eval/FROZEN.md` is committed, before any code for T-14 or J-15.

<!-- T-05 dropped on 2026-11-01 (D-82): approvals, proposal fields and cost are scored by code against the president's labels; human graders could not add to that. -->

### T-06 Baseline prompts
- Owner: tatiana
- Status: review
- Needs: T-04
- What: The comparison versions: a plain checklist (no model); the plain model, no memory; the same model with the OSA rulebook pasted in. Same events, same output format as ClubOps. Record every response (replay mode). Note the manual time from T-29.
- Done when: all baselines run on all test events and responses are recorded.

### T-07 Collect the missing AUB documents
- Owner: tatiana
- Status: todo
- Needs: none
- What: Student Life Handbook (Tala, end of October); save the policytech documents as PDF (Athletics facilities, Code of Conduct, Online Communication Policy).
- Done when: all are in the private data folder.

### T-08 Enter the AUB rules (shared rulebook)
- Owner: tatiana
- Status: done
- Needs: T-07, T-12
- What: Turn the OSA rules into rule items in the General store, each with source and authority. Verify each one.
- Done when: every rule in the approval-code key exists as a verified rule item with its source.
- Progress (2026-10-23): 25 rules in `data/rulebook/aub-rules.json`, reviewed and approved by Tatiana (D-66).

### T-09 Seed the Running Club know-how
- Owner: tatiana
- Status: doing
- Needs: T-12, T-18
- What: Teach ClubOps the club's main tips, contacts and sponsors (president notes; old-chat import only if time allows).
- Done when: Knowledge shows the club's core facts, approved.
- Progress (2026-11-06): `scripts/seed_club.py` read the club's chats and files (107 pieces, $0.14): 161 facts wait in Review. Tatiana marks them on the review sheet (approve / reject / edit, and whether each is shared with all clubs), then `apply`. The first sheet held many one-time arrangements and personal opinions (F-167): learning now drops them (D-95). The sheet was reviewed and applied on 2026-11-07 (38 of 161 approved). Learning the bylaws on top of it then surfaced F-168 (see T-45).

### T-10 Model client
- Owner: tatiana
- Status: done
- Needs: none
- What: One OpenAI-compatible client with replay / record / live modes, a cost budget per call and per plan, and validation of the output against the contracts. Branch `feat/model-client-and-redaction`.
- Done when: merged, with tests; `make check` passes without API keys.

### T-11 Redaction
- Owner: tatiana
- Status: done
- Needs: none
- What: Replace phones, AUB IDs, emails and links before any text reaches the model (D-09, D-36). Don't redact money ranges like "1500-3000".
- Done when: merged with tests, including false-positive cases.

### T-12 Storage (SQLite)
- Owner: tatiana
- Status: done
- Needs: none
- What: General store (AUB-wide), one store per club, with full-text search (D-35). Contacts, assets and event history get their tables in T-13, once their contracts exist.
- Done when: the existing store tests pass on SQLite.

### T-13 Contract changes for the new scope
- Owner: tatiana
- Status: done
- Needs: none
- What: Add to the contracts: "not sure" answers with `ask` and `look_in`; agent runs (steps, questions, step and cost limits); event status; calendar items (see `docs/calendar-contract.md`); drafts (`DraftRequest` → `Draft`, used by Joey's templates); contacts (D-10), assets (D-12) and event history (D-21), with their SQLite tables. Bump versions, run `make schemas`.
- Done when: merged; Christophe and Joey told what changed.

### T-14 Event planner agent
- Owner: tatiana
- Status: done
- Needs: T-04, T-10, T-12, T-13
- What: The agent loop: it chooses its own steps (search memory, look at similar past events, check rules, check calendar clashes, fill the proposal), asks the user when information is missing, and stops at 8 steps or $0.05.
- Done when: it plans an event end to end and shows its steps; tests cover the limits and a missing-info question.

### T-15 Rules, approvals list and deadlines
- Owner: tatiana
- Status: done
- Needs: T-08, T-13
- What: Apply the rules to an event (`apply-rules`), list the approvals, compute task due dates backward (`plan-backward`), warn when a lead time has passed.
- Done when: works on the test events with uncertain rules marked, never silently skipped.

<!-- T-16 moved to J-12 on 2026-10-24: it fits Joey's part and lightens Tatiana's load. -->
<!-- T-17 moved to J-15 on 2026-10-24: Joey builds the chatbot; Tatiana keeps the club know-how it answers from. -->
### T-18 Learning inputs and the approval gate
- Owner: tatiana
- Status: done
- Needs: T-11, T-12
- What: Turn chat teaching, the after-event form, forwarded OSA emails and uploaded documents (including past expense forms, kept as a price list) into proposed facts; merge repeats; detect contradictions; flag outdated documents. Nothing is saved until approved in Review.
- Done when: each input type produces Review cards; approve / reject / merge work.
- Progress (2026-10-29): chat teaching, after-event form and document upload (text and .xlsx; expense forms -> price list) live in the app; `Learner.learn` is ready for J-10's forwarded e-mails (pass a `CaptureRequest`). Real-model quality is checked in T-26 once the key arrives.

<!-- T-19 moved to C-19 on 2026-10-24: it fits Christophe's part and lightens Tatiana's load. -->
<!-- T-20 moved to C-21 on 2026-10-24: it fits Christophe's part and lightens Tatiana's load. -->
<!-- T-21 moved to J-11 on 2026-10-24: it fits Joey's part and lightens Tatiana's load. -->
### T-22 Backend API for the UI
- Owner: tatiana
- Status: done
- Needs: T-13
- What: Every endpoint in the UI spec's API table, same field names; sign-in (decide the method with Christophe, see C-01).
- Done when: Christophe can switch from fake data to the real API (C-13).
- Progress (2026-10-24): part 1 live (sign-in, events, runs, approve, tasks, calendar, knowledge, review, cabinet, usage); see `docs/api.md`. Part 2 (drafts, after-event, teach, handover, documents, setup) answers 501 until those tasks are built.

<!-- T-23 moved to C-20 on 2026-10-24: it fits Christophe's part and lightens Tatiana's load. -->
<!-- T-24 moved to J-13 on 2026-10-24: it fits Joey's part and lightens Tatiana's load. -->
<!-- T-25 moved to C-18 on 2026-10-24: it fits Christophe's part and lightens Tatiana's load. -->
### T-26 Run the final evaluation
- Owner: tatiana
- Status: todo
- Needs: T-06, T-14, T-15, J-12, J-15, T-38, C-27, J-17, J-19, J-20, T-44
- What: Plan the held-out events with every baseline and with ClubOps (3 runs each, report the spread), plus ClubOps with an empty club memory (rules-only score) and the ASME events (D-50); automatic check against what really happened (approvals, proposal fields; no human graders, D-82); chatbot test; learning test; cost per successful plan; both start settings (full and short start, D-92) with "found or flagged" next to false alarms, and model vs tool time per step; the new-club test and learning curve (J-20: ASME and synthetic clubs starting empty, D-91). The measured real-world constraint (brief: "identify and evaluate at least one") is cost: run ClubOps with a one model, Claude Haiku 5.5, chosen in a measured 4-model trial (`results/model-trial.md`, D-90); report its quality, latency and cost per plan. Commit sample traces (metadata only) in `traces/samples/`. Fix what it finds and turn each failure into a regression test.
- Done when: result tables in `results/` (the model trial is in `results/model-trial.md`), reproducible with `make eval`.

### T-27 Report and evidence numbers
- Owner: tatiana
- Status: todo
- Needs: T-26
- What: Final report from the design log: problem, evaluation and results chapters, plus putting the whole report together (Christophe and Joey write their own sections in C-29 and J-13). Update `docs/evidence.md` so every number matches the new results. Poster: J-18. Demo: C-28.
- Done when: submitted by 30 November.

### T-28 Coordination
- Owner: tatiana
- Status: doing
- Needs: none
- What: Share the UI spec link with Christophe and `docs/calendar-contract.md` with Joey; confirm D-36 (links hidden) and D-38 (French) in the design log; answer the open questions in the UI spec.
- Done when: both teammates confirmed they started; D-36 and D-38 marked decided.

### T-29 Evidence for the problem and the poster claims
- Owner: tatiana
- Status: todo
- Needs: none
- What: Short, consented notes from the 4 cabinet interviews (Running Club, ACM, IISE, Math Society): their process, submissions sent back, time spent. A timed walkthrough of one real event's paperwork. Write `docs/problem.md` (user, current workflow, pain, why an agent).
- Done when: every problem claim in `docs/evidence.md` points to a note or a timing.

<!-- T-30 moved to C-22 on 2026-10-24: it fits Christophe's part and lightens Tatiana's load. -->
<!-- T-31 moved to C-29 on 2026-10-31: docs and setup fit Christophe's deploy work; Tatiana keeps the club data and evaluation. -->

### T-32 Real pilot event
- Owner: tatiana
- Status: todo
- Needs: C-18, C-14
- What: Plan one real Running Club event in November with ClubOps on the deployed app. Record the cabinet's time, what ClubOps caught or missed, and their feedback.
- Done when: a short pilot write-up in `results/`, used in the report and poster.

### T-33 Handover test
- Owner: tatiana
- Status: doing
- Needs: T-09, C-19
- What: Run the protocol in `eval/handover-test.md` (D-74): 8 volunteers (AUB students, none on the cabinet or team), 10 frozen questions in two sets of 5; each person answers one set with the old chats and files and the other with ClubOps (chatbot, handover guide, Knowledge), order balanced; blind scoring; 12 to 18 November. Volunteers recruited (2026-10-31); now pick and balance the 10 questions privately now.
- Done when: results in `results/handover-test.md` and the poster claim in `docs/evidence.md` points to them.

<!-- T-34 moved to C-30 on 2026-10-31: it builds on the setup and docs in C-29. -->

### T-35 ASME data (real second club)
- Owner: tatiana
- Status: done
- Needs: none
- What: Ask Alexis (ASME president) for 3-5 past proposals (ideally a workshop, trip or conference), what each really needed, his OK to use them privately, and a 10-minute setup chat later. Remove phone numbers and IDs.
- Done when: ASME events and their real approvals are in the private eval folder.
- Progress (2026-10-23): Alexis sent 4 proposals (screen recordings) and 12 expense forms. 15 ASME events drafted privately in `clubops-raw/eval/asme-events.csv` with guessed approvals; personal details removed. Left: Alexis fills the real approvals (column `approvals_real`) and confirms the open questions in `notes`.

<!-- T-36 moved to J-14 on 2026-10-24: it fits Joey's part and lightens Tatiana's load. -->
### T-37 Other presidents' questions
- Owner: tatiana
- Status: done
- Needs: none
- What: Take the real questions from the presidents' group, reword them with no names (D-51), write the correct answer or "not sure, ask X" from OSA staff replies and documents.
- Done when: added to the chatbot test before T-04's freeze.

### T-38 Freeze the other-club test sets
- Owner: tatiana
- Status: done
- Needs: T-35, J-14
- What: Same as T-04 for the ASME events and the made-up events: held-out split, hashes in `eval/FROZEN.md` (Freeze 2).
- Done when: Freeze 2 is filled in, before the generalization run in T-26.


### T-39 Create the ClubOps Gmail inbox
- Owner: tatiana
- Status: doing
- Needs: none
- What: Create one Gmail account for ClubOps (the service, not one club), e.g. clubops.inbox@gmail.com, owned by the team. Turn on 2-step verification. Give Joey access for J-10. Its password and tokens live only in a password manager and the host's settings, never in the repo.
- Done when: the account exists and Joey can open it.

- Progress (2026-10-31): account created. Left: turn on 2-step verification, store the password in a password manager, and give Joey access for J-10.
### T-40 Branch protection and reviewed pull requests (bonus)
- Owner: tatiana
- Status: doing
- Needs: none
- What: Get GitHub Pro free with the GitHub Student Developer Pack (education.github.com/pack), which allows branch protection on a private repo. Protect `main`: changes only through a pull request, 1 approving review from another teammate, all checks green, no force pushes. Then every PR is reviewed by someone other than its author (the reviewer leaves at least one real comment or approval). The Projects board and weekly sprints moved to C-31.
- Done when: `main` is protected and the PR history shows reviews by teammates from then on.
- Progress (2026-10-31): GitHub Student Developer Pack approved on 31 October; benefits (GitHub Pro, needed for branch protection on a private repo) become available after 72 hours, around 3 November. Then: protect `main`.
---

### T-41 Shared AUB layer (any club, D-91)
- Owner: tatiana
- Status: done
- Needs: T-18
- What: Facts true for every AUB club (offices, forms, rooms, deadlines) are proposed for the shared layer; club-only facts stay in the club. Only a president approves a shared fact, can change ClubOps' guess either way (Review `shared`, seeding sheet `share_with_all_clubs`), and a club can never pull a shared fact into its own layer (F-163).
- Done when: an approved AUB fact is seen by a brand-new club, with tests (`tests/test_shared_layer.py`).

### T-42 Ask, don't guess, when a club knows little (D-91)
- Owner: tatiana
- Status: done
- Needs: T-14
- What: When memory has nothing approved, the planner is told to ask the user instead of guessing; an AUB tip learned from a club is labelled "not an official rule" (planner-v4). Learning from use already exists (after-event notes, teaching in chat).
- Done when: `tests/test_planner_agent.py` covers both notes.
- Also (2026-11-06, D-93): a plain-code self-check before finishing asks once about "not sure" rules while a fact is missing (planner-v5).

### T-43 Prompts fit any club (D-91)
- Owner: tatiana
- Status: done
- Needs: none
- What: A test reads every app prompt from the code and fails if one names a club, a sport or a club's own places, so tuning on one club's events can't leak into the prompts (F-164).
- Done when: `tests/test_prompt_neutrality.py` passes.

### T-44 Onboarding material for the new-club test
- Owner: tatiana
- Status: todo
- Needs: T-35, J-20
- What: Updated 15 Nov to the setup interview (D-103) instead of pasted documents. Before the day: add the ASME president's account (sign-in Gmail, private). On 18 or 19 November the president answers the setup interview (one small model call per answer) and reviews the cards like a busy president, no special care. Leak check: no answer may name a test event or give away a labelled approval or deadline; such an answer is removed before the run. Then J-20's runner plans ASME's 13 frozen events.
- Done when: answers and cards are in `data/private/asme/` and the leak check table in `eval/FROZEN.md` is filled.

### T-45 A cut-off model answer is reported, not dropped in silence (F-168, F-169)
- Owner: tatiana
- Status: done
- Needs: T-09
- What: Learning the bylaws printed "all done" while only 1 of its 4 pieces had reached the model: the other answers were cut off at the answer limit, which looked like "not JSON", and the pieces were counted as empty and marked done. Read the provider's stop signal on every call, count such a piece as failed (not skipped) and leave it out of `done` so a rerun retries it; split documents on their own headings so a rule is not cut in half.
- Done when: a cut-off answer says so, a failed piece is retried on the next run, and both have a regression test. (2026-11-08: done, D-98; contracts 0.2.3.)

### T-46 Connect Google Calendar on the backend
- Owner: tatiana
- Status: todo
- Needs: T-22
- What: Keep Google sign-in separate from Calendar authorization. Add president-only connect/disconnect and OAuth callback endpoints with state validation, server-side encrypted refresh-token storage and refresh/reconnect handling. Use the private club calendar ID, `calendar.events` and `calendar.acls` scopes. After an approved plan is saved, drain Joey's sync queue to Google and report pending/error/connected status. On cabinet add/remove, use Joey's J-21 reader ACL adapter with retryable failures; never grant writer or owner access. Agree the endpoint response fields with Christophe before changing the UI contract.
- Done when: synthetic API tests prove unauthorized users cannot connect, unapproved plans never sync, retries do not duplicate events, and cabinet add/remove grants/revokes only reader access; a cabinet-approved local Google test completes after J-01's private calendar ID is supplied.

### T-47 OSA e-mail reaches Review: API and accounts (D-113, D-114)
- Owner: tatiana
- Status: doing
- Needs: J-10, T-39
- What: The parts that need the API owner or her accounts. Gmail read access for `clubops.agent` (`gmail.readonly`, refresh token only in `.env`). The private OSA sender list (operator data, never the repo). Routes in `app.py`: add/verify an extra sending address, `GET /api/inbox` (cabinet only, own club), `POST /api/inbox/{id}/capture` (one paid model call, triggered by a click). Prompt caching for the fixed capture instructions. Inbox checks are J-22; screens are C-35.
- Done when: a real forwarded OSA e-mail becomes Review cards for its club through the routes, with synthetic route tests and failure-matrix rows.

### T-48 Expiry archive and AUB-wide cards (D-115)
- Owner: tatiana
- Status: todo
- Needs: T-47
- What: Each card can carry an expiry date (the model suggests it, the reviewer can change it); a plain rule, no model, moves an expired card to an archive the planner never uses; the president can restore it; the archive is kept. Cards are sorted AUB-wide or club-only: AUB-wide cards are approved by the operator now (later: live when two presidents approve), club-only cards by the president. After ASME and the final evaluation: simple approved rules (date cut-offs) checked by code in the planner, and reading OSA e-mails without a click.
- Done when: synthetic tests for expiry, restore and the two card kinds, each with a failure-matrix row.
- Progress (2026-11-15): expiry and AUB-wide sorting already existed (D-124); added the president's restore route with tests (F-215). Still after the final evaluation: planner date checks in code, reading OSA e-mails without a click.

## Christophe: frontend

### C-01 Read the UI spec and pick the stack
- Owner: christophe
- Status: done
- Needs: none
- What: Read the UI spec. Choose any framework that deploys on the same free host. Agree the sign-in method with Tatiana (AUB email link or Google sign-in).
- Done when: stack and sign-in written in `docs/design-log.md` (one row each).

### C-02 App shell
- Owner: christophe
- Status: done
- Needs: C-01
- What: Layout, sidebar with badges, top bar, routes, roles (adviser read-only: buttons hidden), phone layout at 375 px.
- Done when: every route opens with placeholder content on desktop and phone.

### C-03 Shared components
- Owner: christophe
- Status: done
- Needs: C-02
- What: Source chip, origin tag, "not sure" card, approve bar, draft card, status badge, agent steps panel.
- Done when: each component is used on at least one screen with fake data.

### C-04 Fake API
- Owner: christophe
- Status: done
- Needs: C-01
- What: Serve the example JSON from the UI spec for every endpoint in its API table, so all screens work without the backend.
- Done when: switching to the real API is one setting.

### C-05 Events screens
- Owner: christophe
- Status: done
- Needs: C-03, C-04
- What: Event list; new-event flow (describe, check details, agent steps panel with questions); event page with its 6 tabs; plan approval bar; run planner warning.
- Done when: the full flow works on fake data.

### C-06 Chat screen
- Owner: christophe
- Status: done
- Needs: C-03, C-04
- What: The four reply kinds, thumbs up/down with "what was wrong", paste a document.
- Done when: works on fake data.

### C-07 Review screen
- Owner: christophe
- Status: done
- Needs: C-03, C-04
- What: All card types, filters, grouping by source, approve all (facts only, never rules).
- Done when: works on fake data.

### C-08 Calendar screen
- Owner: christophe
- Status: done
- Needs: C-03, C-04
- What: Month view read from ClubOps, my tasks / all, item details, Google sync status.
- Done when: works on fake data.

### C-09 Knowledge screen and fact page
- Owner: christophe
- Status: done
- Needs: C-03, C-04
- What: The 5 tabs, plain search, fact page with sources and history.
- Done when: works on fake data.

### C-10 Handover screen
- Owner: christophe
- Status: done
- Needs: C-03, C-04
- What: Role picker, role guide with gaps, download, "ask about this role".
- Done when: works on fake data.

### C-11 Settings and new-club setup
- Owner: christophe
- Status: done
- Needs: C-03, C-04
- What: Cabinet, Google connection, OSA email inbox, documents, AI cost; the setup flow.
- Done when: works on fake data.

### C-12 States and cost rules
- Owner: christophe
- Status: done
- Needs: C-05
- What: Loading, empty, error and fallback states from the spec; AI buttons disabled while running; nothing calls AI on page load.
- Done when: every state in the spec's table can be shown.

### C-13 Connect to the real backend
- Owner: christophe
- Status: doing
- Needs: C-12, T-22
- What: Switch from fake data to the real API; fix mismatches with Tatiana.
- Done when: every screen works on the deployed backend.
- Unblocked (2026-10-24): T-22 part 1 is live. `docs/api.md` answers `web/API_NOTES.md` (conventions, sign-in, what is live and what answers 501). Always send `X-Requested-With: ClubOps` on changes, also without a body.
- Progress (2026-10-26): available planning, approval, calendar, handover, usage and session flows pass against the local API and production router. Google credential exchange is implemented; real Google/deployed verification needs configuration. Remaining 501 features depend on J-15/T-18/C-21/J-07 and the API owner.
- Progress (2026-11-01): integrated T-18 warning/outdated fields, supported uploads and no-fact replies. A real Caddy/API repeat exposed intermittent SQLite member-lookup errors (issue #45, API owner); production-flow completion remains open despite passing scripted/Vite and container checks.
- Progress (2026-11-02): #47 fixes the SQLite connection race; the same Caddy/API suite now passes all 4 cases with no ASGI/SQLite exceptions in the captured log. Deployed Google/every-screen verification remains pending.

### C-14 Deploy the frontend
- Owner: christophe
- Status: todo
- Needs: C-13, C-18
- What: Deploy on the same free host as the backend.
- Done when: the cabinet opens the app from a link on their phones.
- Preparation: the shared Docker image and Caddy router are ready for a container build; see `web/DEPLOYMENT.md`. No deployed URL yet.
- Note (2026-11-11, Tatiana): add the deployed app's address to "Authorized JavaScript origins" of the Google client "ClubOps Web Client" (it lists only http://localhost:5173), or Google sign-in fails on the live site.

### C-15 Demo support
- Owner: christophe
- Status: todo
- Needs: C-14
- What: Fix what the final test finds; help with the demo.
- Done when: demo day.

### C-16 Repair the frontend PR dependency audit
- Owner: christophe
- Status: done
- Needs: C-12
- What: With Christophe's explicit authorization, update the vulnerable Python dependency blocking PR #9, verify the locked environment and CI, and record the handoff.
- Done when: the dependency audit and existing PR checks pass without disabling security checks.

### C-17 Sync main and check contracts 0.2.0
- Owner: christophe
- Status: done
- Needs: C-12
- What: Merge the latest main into the frontend branch, preserve both teammates' work, and check frontend models against the published 0.2.0 contracts without inventing API endpoints.
- Done when: merge conflicts are resolved, confirmed frontend mismatches are fixed and tested, remaining T-22 agreements are documented, and checks pass on the updated PR.


### C-18 Deploy the backend (was T-25)
- Owner: christophe
- Status: doing
- Needs: none
- What: Put the backend (`uvicorn clubops.api.app:build --factory`) on the same free host as the frontend (Render, D-47), with a persistent disk for `CLUBOPS_DATA_DIR` and the secrets from `.env.example` in the host's settings, never in the repo. Load the rulebook and add the president (`scripts/load_rulebook.py`, `scripts/add_member.py`). Deployment files (`render.yaml`, `Dockerfile`) are yours; ask Tatiana before changing Python code.
- Done when: the cabinet signs in on the deployed app and plans an event.
- Progress (2026-11-01): production and local Docker targets build and run; Compose browser checks and data/session persistence across container replacement pass. Production refuses local auth settings. Real Google client ID, hosting account/budget and provider configuration remain unknown. Render Free cannot attach a disk; the prepared paid service must be reviewed before provisioning (`web/DEPLOYMENT.md`). No deployed URL yet.

### C-19 Handover endpoint (was T-19)
- Owner: christophe
- Status: done
- Needs: none
- What: Serve the Handover screen from the club's approved facts. The assembly already exists in `src/clubops/knowhow/handover.py` (plain code, no AI); write `src/clubops/api/handover.py` that turns its `HandoverPack` into the screen's `HandoverGuide` (sections, entries with sources, gaps with who to ask and where to look) and register it in `api/app.py` in place of the 501 route (one line; tell Tatiana). Synthetic data in tests.
- Done when: `GET /api/handover/{role}` returns the guide for each role, with tests for an empty club and a club with gaps.

### C-20 Cost and trace report (was T-23)
- Owner: christophe
- Status: doing
- Needs: none
- What: Cost, tokens, latency, retries and failures per feature from the traces (`clubops.tracing`, metadata only) and the agent runs; cost per successful plan. A script writes the report to `results/`; `GET /api/usage` shows the real numbers per feature for the Settings screen. Code in `src/clubops/reports/` (yours) plus the usage route (tell Tatiana).
- Done when: the report in `results/` and the Settings numbers come from real runs.
- Implementation: `python -m clubops.reports --club <club> --month YYYY-MM --output results/usage.json`; API run metadata is collected automatically. Trace metrics are club-scoped and explicitly unavailable until the relevant feature writes them; legacy monthly planning spend remains available.
- Validation remaining: generate the report from real provider activity during the pilot and have feature owners supply club-scoped token/latency/retry traces. Scripted local runs prove the reporting path, not production cost measurements.

### C-21 New-club setup (was T-20)
- Owner: christophe
- Status: doing
- Progress (2026-11-11): #87 is merged and wires the route plus `/me` completion from the owned service. Local synthetic integration checks pass; actual new-club/deployed acceptance remains open. Earlier route-wiring blockers below are historical.
- Onboarding decision (2026-11-09): per Tatiana's message relayed by Christophe, setup questions are the primary onboarding path; WhatsApp history import is dropped for onboarding because members have not consented. ASME is planned for Wednesday 11 November via this flow. #55 contains current main/contracts 0.2.3 and is mergeable; Tatiana will wire the API after merge. UI/guide say no chat history is required and use one tab (D-103). No professor privacy answer is claimed.
- Owner response (2026-11-09): Tatiana's #43 reply requests #55 be made ready so she can wire the route and `/me`; she declines the question-token extension and accepts the documented one-tab limit (F-151). Actual ASME seed material belongs to T-09. Synced current main; reported `sources_failed` now leaves setup retryable before queueing any partial facts (F-174). Production wiring and real second-club verification remain pending.
- Needs: none
- What: The backend for the setup screen you built (C-11): `POST /api/setup/next {answer?}` walks a new club through about 10 questions (name, club or society and faculty, adviser, cabinet roles, signature events, usual venues, sponsors...) and turns each answer into a proposed fact in Review; the 25 AUB rules apply from day one (they are shared). Code in `src/clubops/api/setup.py` (yours); register it in place of the 501 route (one line; tell Tatiana). Tatiana gives you ASME's non-personal facts to seed ASME as the second club for the demo.
- Done when: a new club can go through setup in the demo, and ASME is the second club.
- Date change (2026-11-11, Tatiana): ASME onboarding moves from Wednesday 11 November to **Wednesday 18 or Thursday 19 November** (moved again on 15 Nov).
- Progress (2026-11-11, Tatiana): production wiring done (D-112). `app.py` registers the setup router with the specified callbacks in place of the 501, and `/api/me` reports `setup_complete` from the service, with the Running Club marked as set up before C-21. The setup tests now run the production route with synthetic callbacks via `create_app(setup_overrides=...)`: deleting the route from `app.router.routes` no longer takes effect in FastAPI 0.162, so they had been exercising the production route. Decided-card retry: pending and approved proposals are skipped; a rejected one can reappear once (F-201, known limit). Remaining: ASME goes through setup in the demo.
- Progress (2026-11-03): owned service/router and frontend in PR #55; durable per-club questions, Untrusted capture, retry outbox and Review-only writes. 18 synthetic service/HTTP/SQLite cases include one explicit reproduction of the unresolved stale-tab limit (F-151), plus desktop/phone setup tests. See `web/CLUB_SETUP.md`. Still doing: Tatiana must wire the public callbacks and `/me` completion field, approve decided-card retry semantics and provide sourced non-personal ASME seed facts. Existing answer-only contract's stale-tab limit is documented; no contract was silently extended.

### C-22 Evaluation in CI (was T-30)
- Owner: christophe
- Status: todo
- Needs: T-26
- What: `make eval` runs from recorded model answers (no API keys) in the CI workflow and fails if a key number drops below its threshold (e.g. approvals missed, invented answers). Tatiana gives the thresholds with the T-26 results.
- Done when: the CI workflow runs `make eval` with regression gates.

### C-23 Frontend checks in CI (bonus)
- Owner: christophe
- Status: done
- Needs: none
- What: Add a CI job for `web/`: install from the lockfile, lint, type check, unit tests and a production build, so a broken screen fails the PR like broken Python does.
- Done when: the CI workflow runs the web job on every PR and it is green on `main`.
- PR #44 merged with individual commits preserved; quality/browser/API/BuildKit checks are green on main `d5dfb17` (2026-11-02).

### C-24 Docker Compose (bonus)
- Owner: christophe
- Status: done
- Needs: C-18
- What: A `docker-compose.yml` that starts the whole app locally (API + web, data on a volume, settings from `.env`) with one command, matching the deployed setup. Document it in the README.
- Done when: `docker compose up` on a fresh clone gives a working app with dev sign-in.
- PR #44 merged: `docker compose up --build` starts the complete local app on loopback with a volume and synthetic cabinet account. Desktop/phone login/routing and actual container replacement/data/session persistence are verified locally and green in main CI. Public deployment remains C-18/C-14.

### C-25 OpenTelemetry traces (bonus)
- Owner: christophe
- Status: doing
- Progress (2026-11-10): optional metadata-only OTLP/HTTP JSON exporter and isolated Jaeger demo implemented in the owned reports folder. Actual local readback/UI show one synthetic run, two steps and two calls; see web/observability/README.md and its evidence. Export defaults off, checks explicit correlation/windows, and allowlists public labels. C-20 real-provider validation and real agent/model producer hooks remain with the owners; no production tracing/monitoring claim, so this stays doing.
- Needs: C-20
- What: Export the existing trace records (metadata only: capability, prompt version, model, latency, tokens, cost, retries, status; never prompts or personal data) as OpenTelemetry spans, one trace per agent run with a span per step and per model call, so they can be viewed in a tool such as Jaeger or Langfuse. Off unless an exporter endpoint is set.
- Done when: a local run shows one agent run as a trace with its steps, and a test checks no prompt text or personal data is exported.

### C-26 Live monitoring of the deployed app (bonus)
- Owner: christophe
- Status: todo
- Needs: C-18
- What: Monitoring that works on the deployed app itself, not only locally. Christophe picks one, both have a free plan and need no extra server: **(a) Grafana Cloud** (hosted Prometheus + Grafana): the app pushes its metrics and traces with OpenTelemetry (this also delivers C-25) — request count and latency per endpoint; model calls, tokens, cost, retries and failures per feature; agent runs by outcome and steps used — with a dashboard (latency, cost per plan, error rate, runs at their limit) and one alert rule; or **(b) Sentry**: errors and slow requests from the API and the web app, with an e-mail alert. Either way: no names, e-mails, prompts or event text in any label or event (scrubbed before sending), keys only in the host's settings, and the dashboard or alert setup exported into the repo.
- Done when: using the deployed app makes numbers or errors appear in the tool within a minute; a test checks nothing personal is sent; a screenshot goes in the report.

### C-27 Learning test runner
- Owner: christophe
- Status: done
- Review fixes (2026-11-09): addressed Tatiana's two blockers on #54: the frozen `fact` column can serve as source and expected fact; chat/after_event_form/forwarded_email map to the existing SourceKind values. Original CSV bytes stay unchanged, question stays separate, unknown kinds remain errors. Synced main `4b3f17e` and refreshed only synthetic prompt recordings. All 70 C-27 tests and full root gates pass (580 passed, 1 skipped; 92.69% coverage); 40 frontend units/build pass. Awaiting Tatiana's re-review, private run and ratings.
- Needs: none
- Merged (2026-11-09): #54 landed on main as 4bed33c after Tatiana confirmed both blockers were fixed and all five checks passed. Runner/blank export/offline scoring are complete; actual private ratings and measurements remain T-26.
- What: Run the frozen learning cases through learning, sandbox approval and the follow-up question; export a private seven-column sheet (id, expected fact, actual saved facts, question, actual answer, blank learned/answer_ok). Tatiana marks yes/partly/no for the ten tests; a second offline command makes the category-count results table, preserving costs/errors. Build/test on synthetic data; Tatiana runs the private file in T-26. Exact-word matching is a smoke diagnostic only.
- Done when: `scripts/eval_learning.py export` produces the blank review sheet and `score` summarizes completed ratings on synthetic data in replay mode, with tests.
- Revision (2026-11-03): Tatiana's review relayed by Christophe replaces automatic exact-word quality scoring with a private review sheet: expected fact, learned fact, question and actual answer, plus blank learned/answer_ok ratings (yes/partly/no). A second offline command summarizes the completed sheet. Exact matching is retained only as an explicitly named technical smoke diagnostic, not learning/answer correctness.
- Implementation (2026-11-02): isolated capture -> sandbox verification -> cited follow-up; exact pre-labelled statement/alias scoring, wrong/missed/duplicate facts and budget costs. Frozen column mappings and plain-text labels are supported without rewriting input. Checked-in synthetic replay runs with no key/network; 20 evaluator tests cover the real pipeline, privacy, failure accounting and replay. See `web/LEARNING_EVALUATION.md`; real private T-26 results are not claimed.
- Revised implementation (2026-11-03): `export` writes the exact seven-column private CSV and two empty rating columns, preserving original IDs and actual saved facts/answers; `score` validates completed yes/partly/no labels and makes an offline results table. Partly is unweighted; every original case, operational error and failed spend remains visible. Exact-word metrics require explicit `smoke`. All 48 C-27 tests pass; real Tatiana ratings and private T-26 measurements remain pending. D-87 supersedes D-83 for quality scoring.

### C-28 Demo script and backup video
- Owner: christophe
- Status: doing
- Review update (2026-11-11): main #87 setup wiring retained. The seven-chapter script/rehearsal now shows the primary president interview (D-103), a pending fact and explicit pause/resume without resubmitting. Current synthetic silent take is 301.60 seconds; the previous six-chapter evidence is historical. Real deployed/team/narrated acceptance remains pending.
- Progress (2026-11-10): five-minute presenter script and isolated synthetic HTTP/UI rehearsal prepared. Desktop/phone checks pass; a 301.56-second silent take has six passing chapters, zero unexpected requests, a verified video checksum and inspected frames (web/demo/evidence). Fresh checked output paths preserve previous takes. C-14/C-18 deployment, real backend/model/security outcomes, team rehearsal and final narrated backup remain pending; this stays doing.
- Needs: C-14, C-18
- What: `docs/demo-script.md`: 5 minutes on the deployed app, showing what the brief asks: one normal plan, then edge cases (missing facts → the agent asks; the step limit; a hidden instruction in an uploaded document; a member without rights trying to approve). Seed a demo club with synthetic data only. Record a backup video in case the network fails on demo day.
- Done when: the script runs start to end on the deployed app, rehearsed once with the team, video saved.

### C-29 Keep the docs true (was T-31)
- Owner: christophe
- Status: doing
- Progress (2026-11-09): refreshed owned architecture, memory and provenance docs against main `4b3f17e`: green main CI evidence, lasting/this-term filtering, failed-source retries, wrong-replacement review limit, shared-scope approval and private debug/review-sheet content. Setup's accepted one-tab limit and owner integration are explicit. Fresh teammate setup and final deployed verification remain open.
- Needs: T-22
- What: Update `docs/architecture.md`, `docs/data-provenance.md`, `docs/knowledge-base.md` and the README setup to the new scope (agent loop, learning, web app, deployment, monitoring). Ask Tatiana when unsure how the backend works. Setup must work from a fresh clone in one command. Write the report sections on architecture, the web app, deployment and monitoring.
- Done when: Joey sets the project up from the README alone; report sections handed to Tatiana.

### C-30 Make the repo easy to grade (was T-34)
- Owner: christophe
- Status: todo
- Needs: T-27, C-22, C-29
- What: The grader is likely an AI agent reading the repo. Add a "How to grade this project" section at the top of the README: each rubric item → the file that proves it → the command that reproduces it (see `docs/plan.md`). Then have a fresh AI session, with no context, grade the repo against the rubric and fix every gap it finds.
- Done when: a fresh-session review finds no rubric item without evidence.

### C-31 GitHub Projects board and weekly sprints (bonus)
- Owner: christophe
- Status: blocked
- Owner response (2026-11-09): Tatiana reports the existing ClubOps board is in the repo's Projects tab with Christophe as admin; weekly sprints start 4 November and reviews are Wednesdays after office hours. Local plan now targets Nohra2005/ClubOps and that cadence; no duplicate board should be created. Current-main dry run reads 85 tasks. Projects scope is still missing; live owner/number/access/fields/cards/iterations and safe adoption of any manual cards must be inspected before sync. No actual weekly review is claimed here.
- Needs: none
- What: A GitHub Projects board fed by `TASKS.md` (one card per task, columns = status), so ownership is visible on GitHub. One-week sprints (a Projects iteration per week with the tasks planned for it); a 10-minute review with the team each week, noted in one line under T-28.
- Done when: the board matches `TASKS.md` and 3 weekly sprints are recorded.
- Progress (2026-11-03): PR #55 adds the pinned TASKS.md plan, private Projects v2 create/sync CLI, board fields, proposed weekly iterations and read-back verification. 12 synthetic tool tests run in web CI; dry run reads 77 tasks from main. See `web/PROJECT_BOARD.md`.
- Blocker (updated 2026-11-09): Projects scope is now enabled for chrs-005, but full read-only discovery returns no visible boards under Nohra2005, chrs-005 or the repository. Need Tatiana's direct board URL/access before inspecting and adopting the existing board; do not create a duplicate. Three actual weekly team reviews still need evidence under T-28; planned iterations are not completed-review evidence.

<!-- C-32 dropped on 2026-11-01 (D-82): no human graders, so no blind grading packets. -->


### C-33 Starter onboarding for a new club (D-91)
- Owner: christophe
- Status: doing
- Progress (2026-11-10): implemented the four starter checks after the explicit server-confirmed interview: cabinet/settings action, two confirmed document uploads and places/partners acknowledgement. Ticks are metadata-only, browser-local per mode/club/member; upload acceptance is distinct from learning/approval. Strict response/file checks, no request on selection, retry preservation and duplicate-click protection have synthetic regressions. Guide: `web/STARTER_CHECKLIST.md`. Local checks pass: 48 frontend units, 12 tool tests, 6 HTTP starter cases, 6 demo/setup cases (including completed-checklist accessibility/phone width), root gates with 600 passed, 1 skipped and 92.68% coverage. C-21 wiring/deployed new-club verification remains open, so this is not marked done.
- Progress (2026-11-10): building the frontend checklist against the existing cabinet/document/setup API while C-21 production wiring and hosting remain pending. Browser-local checklist acknowledgements and accepted uploads will be labelled separately from server interview progress and approved knowledge. No new backend contract or WhatsApp import.
- Needs: C-21
- What: Extend the setup flow into one short checklist every new club does the same way (about 10 minutes): add the cabinet, upload the club's rules or constitution, one past proposal, and its usual places and partners (`POST /api/cabinet`, `POST /api/documents`). Show what is done, and say plainly that ClubOps starts with the shared AUB know-how and learns the club as it is used.
- Done when: a new club can finish the checklist in the deployed app, with a browser test on synthetic data.

### C-34 Review screen guards (D-91)
- Owner: christophe
- Status: done
- Progress (2026-11-10): shared badges and president scope switches send the existing boolean only on confirmed individual decisions; quotes are visible on both sides of comparisons, missing quotes explicit, all disagreements grouped first. Bulk approval skips shared/flagged/disputed cards and unsaved sharing choices. Denied requests preserve edits/choice. Demo matches current T-41 president approval. Guide: `web/REVIEW_GUIDE.md`. Verified: 46 frontend units, 12 board-tool tests, 8 HTTP review cases, 2 demo review cases, 2 full-screen accessibility cases; full root gates with 600 passed, 1 skipped and 92.68% coverage. Awaiting independent PR review; no backend/contract or deployment change.
- Progress (2026-11-09): starting the ready frontend task after T-41 and #55 merged. Implementing shared-scope review controls against the published task/API tests, source quotes on comparisons, disagreement-first grouping and conservative bulk approval. Backend implementation/contracts remain unchanged; setup app wiring stays with Tatiana.
- Needs: T-41
- What: On each Review card show the source quote, a "Shared with all AUB clubs" badge when `shared` is true, and a switch to change it (send `shared: true/false` with the decision; only presidents may approve shared facts, others get 403). Show disagreements first. Bulk approve skips shared facts, disagreements and warned facts (D-79).
- Done when: the screen does this with tests, and the user guide explains sharing in two lines.

### C-35 Inbox, forwarding and card screens (D-113 to D-116)
- Owner: christophe
- Status: todo
- Needs: C-21, C-34, T-47
- What: (1) Setup (C-21): a step to add an extra sending address and show the code to e-mail; an Outlook forwarding guide (OSA senders only) showing the club's `+tag` address with a copy button, and a "Test my forwarding" button. (2) Inbox screen: waiting e-mails, a "Read this" button that says it costs money, and the reason when an e-mail was skipped ("ClubOps only reads e-mails forwarded from OSA staff"). (3) Review cards (C-34): an expiry date field, an AUB-wide / club-only label, an "Add to calendar" box for deadlines (ticked by default) with who it is for, and an archive view with Restore.
- Done when: each screen has frontend tests against the T-47 routes (stubbed until they land) and is in the demo build before the 23 Nov meet-up.

## Joey: calendar, reminders, drafts

### J-01 Read the calendar contract and set up Google
- Owner: joey
- Status: blocked
- Needs: none
- What: Read `docs/calendar-contract.md`. Create the Google Cloud project, turn on the Calendar API, create the shared club calendar. Secrets never go in the repo.
- Done when: a test item appears in the shared calendar from your code.
- Progress (2026-11-10): manual Google setup complete: Calendar and Gmail APIs enabled, External OAuth test users and web client configured, Running Club calendar created, and its ID stored only in local `.env`. No manual calendar sharing is required.
- Blocked: T-46's separate Calendar authorization and backend sync, C-35's connection UI, and a cabinet-approved live test are still needed before a test item can appear in Google Calendar. The adapter and setup steps are in `src/clubops/calendar/README.md`.

### J-02 Sync calendar items
- Owner: joey
- Status: done
- Needs: J-01, T-13
- What: Create, move (same ID, new date), and delete items so Google always matches ClubOps. ClubOps is the boss; edits in Google are overwritten. Only approved plans are sent.
- Done when: tests show no duplicates when an item is sent twice or moved.

- Verified (2026-11-16): Existing fake-Google tests meet this task's synthetic acceptance gate (stable-ID upsert/move, done/cancel, retry and failure coverage). Live authorization/deployment acceptance remains J-01/J-09; D-116 deadline invitations remain J-23. This does not claim live Google delivery.

### J-03 Reminders
- Owner: joey
- Status: doing
- Needs: J-02
- What: Default reminders from the contract; reminders go only to the person holding the task's role; everyone sees the shared calendar.
- Done when: a test task reminds the right person at the right times.

### J-04 Club-wide reminders
- Owner: joey
- Status: doing
- Needs: J-02
- What: Reminders not tied to an event: OSA rule check (monthly from September until the rules are in), cabinet elections (April), impact form after each event.
- Done when: they appear in the calendar with no event attached.

### J-05 Done and cancelled
- Owner: joey
- Status: done
- Needs: J-02
- What: Task done stops its reminders; event cancelled deletes all its items.
- Done when: tested.

- Verified (2026-11-16): Existing fake-Google tests meet this task's synthetic acceptance gate (stable-ID upsert/move, done/cancel, retry and failure coverage). Live authorization/deployment acceptance remains J-01/J-09; D-116 deadline invitations remain J-23. This does not claim live Google delivery.

### J-06 Calendar tests and failure rows
- Owner: joey
- Status: done
- Needs: J-05
- What: Tests with a fake Google (no real calls in `make check`); a Failure Matrix row for each failure mode (Google down, item sent twice, role with no person).
- Done when: `make check` passes with your tests.
- Progress (2026-11-10): fake-Google tests cover approval gating, stable IDs, move, done/cancel, missing-role fallback, all-cabinet private reminders, queue retry and club-wide items. Focused tests pass. Live plan approval, Google sync and role access still require T-46/C-35 and J-01/J-09 acceptance.

- Verified (2026-11-16): Existing fake-Google tests meet this task's synthetic acceptance gate (stable-ID upsert/move, done/cancel, retry and failure coverage). Live authorization/deployment acceptance remains J-01/J-09; D-116 deadline invitations remain J-23. This does not claim live Google delivery.

### J-07 Draft templates
- Owner: joey
- Status: doing
- Needs: none
- What: Templates for: WhatsApp announcement, reminder message, sponsor email, Instagram caption, poster text (never logos), expense form, volunteer shifts, impact report. Match the club's real style (look at past announcements).
- Done when: each template produces a draft a cabinet member would send without edits.
- Progress (2026-10-31): all eight draft types have a writer and synthetic tests. Approved private style examples and cabinet review are still needed to judge send-ready quality.
- Progress (2026-11-10): Joey needs approved past announcements kept in private storage, then two cabinet members to review drafts for three past events under J-08. Do not place examples or feedback in Git.

### J-08 Check the drafts with the cabinet
- Owner: joey
- Status: todo
- Needs: J-07, T-14
- What: Generate drafts for 3 past events; ask 2 cabinet members what they'd change; fix the templates.
- Done when: their changes are in.

### J-09 Calendar on the deployed app
- Owner: joey
- Status: todo
- Needs: J-06, C-18
- What: Google secrets set on the host; sync runs on the deployed backend.
- Done when: approving a plan on the deployed app puts items in the shared calendar.

### J-10 OSA e-mail inbox
- Owner: joey
- Status: doing
- Needs: T-39, T-18
- What: Read the ClubOps inbox (Gmail API) and turn each forwarded e-mail into input for learning. One inbox for all clubs: each club forwards to its own address with a "+" tag (`clubops.agent+running-club@gmail.com`), and the tag says the club. Drop e-mails whose sender is not on that club's cabinet list, and e-mails with an unknown tag. Pass the rest as `Untrusted` text (sender, date, subject, body; attachments listed by name only) to T-18's capture step, so every fact waits in Review. Never auto-approve; never reply to the sender. Code in `src/clubops/inbox/`.
- Done when: forwarding a real OSA e-mail puts a proposed fact in that club's Review, and tests (with made-up e-mails) cover: wrong tag, sender not on the list, the same e-mail twice (no duplicate), and an e-mail with instructions inside ("ignore the rules...") treated as data. Each case has a failure-matrix row.
- Progress (2026-10-31): Gmail read adapter, designated `clubops.agent+<club>@gmail.com` tag/sender filtering and durable deduplicated private queue added with synthetic tests. Human-click capture integration and live forward remain pending Gmail API access and Tatiana's API wiring.

### J-11 Daily check and OSA rule check (was T-21)
- Owner: joey
- Status: doing
- Needs: J-04
- What: A daily plain-code check of each club's upcoming events (overdue tasks, deadlines inside 2 days, plans outdated by edits) that calls the AI only when it finds a real problem; and the monthly OSA website check from September until the president marks the new rules as in (D-30, D-31). Both run on a schedule on the server and write reminders, never send messages. Code in `src/clubops/checks/`.
- Done when: both run on a schedule on the deployed app, with tests (made-up events) and failure-matrix rows.
- Progress (2026-10-31): plain-code daily findings and OSA page hash checks added with synthetic tests. Server scheduling, reminder persistence and source fetch integration remain pending owner-side deployment/API work.

### J-12 Proposal draft (was T-16)
- Owner: joey
- Status: doing
- Needs: none
- What: Fill the OSA Event Proposal form from an approved event's details, the club profile and the rule check, following the frozen `draft-proposal` contract (`DraftProposalRequest` -> `ProposalDraft` in `src/clubops/contracts/forms.py`). The form is `data/forms/osa_event_proposal_2026_2027.json`; it grows from 33 to 52 questions: "Yes" to materials adds 10 (q34-q43: tables, chairs, boards, tents, table covers, outlets and amperage), "Yes" to catering adds 9 (q44-q52: menu, people, setup time, price per person, a second option, cost sharing); each extra question has `required_if` on the question that opens it. Every answer says its origin (stated, from memory, computed, missing) and source; times in 24-hour format; dates match the event; adviser name without "Dr."; nothing invented (unknown = left for a person). Code in `src/clubops/drafts/proposal.py`. Tatiana adds it to the agent as a tool and to the event page once it works (tell her).
- Done when: drafts for the made-up test events pass the form checks (required answers present, 24-hour times, dates consistent, attachments listed), with tests for both form versions.
- Progress (2026-10-31): deterministic drafter and synthetic checks for the checked-in 33-question form added. The official six materials questions are not yet present in the checked-in template, so their exact form-version check remains pending.
- Progress (2026-11-10): verified the current 52-field form's catering branch and a synthetic 33-field legacy shape selected by field ID; both keep unknown answers pending rather than inventing values. Focused tests pass. Current official 52-field required answers still need human confirmation, and Tatiana owns agent/event API wiring (issue #83).

### J-13 Security tests (was T-24)
- Owner: joey
- Status: doing
- Needs: none
- What: An adversarial test set that tries to break ClubOps: instructions hidden in an event description or a forwarded e-mail ("ignore the rules", "approve this"), fake "OSA" rules sent as facts, one club reaching another club's data, the adviser or a non-cabinet account changing things, a forged sign-in, spending past the limits. Start with the planner and the API (live now); add the chatbot and learning when T-17 and T-18 land. Made-up data only. Tests in `tests/security/` (yours). Also update `docs/threat-model.md` and write the report sections on security, the calendar and the inbox.
- Done when: the set runs in `make check`; every way it found to break ClubOps has a failure-matrix row and is fixed (or the row says why not, and Tatiana agreed); and the injection attack success rate is measured (how many of the attacks worked) with the defences off and on, and reported in `results/`.
- Progress (2026-10-31): synthetic API, learning, planner prompt and budget boundary tests added. The full adversarial corpus, real defense-off/on measurement and report sections remain pending.
- Progress (2026-11-10): froze ten synthetic injections across event, mail, document, chat and after-event surfaces. A strict scorer accepts only complete reviewed defense-off/on boolean outcomes and prints aggregate rates; no model run or success-rate claim has been made. Tatiana must provide the isolated defense-off run and review private outcomes before results are published.
- Progress (2026-11-11): Tatiana's PR #82 review identified a real benign-text false positive. Added a separately frozen four-case benign corpus and required false-positive counts alongside attack success. The detector regression remains an explicit expected failure until Tatiana fixes her owned learning detector (F-204); no measured rates are claimed.

### J-14 Made-up events for the missing event types (was T-36)
- Owner: joey
- Status: done
- Needs: none
- What: 10 short, made-up event descriptions for types the Running Club never ran (workshop, conference, film screening, concert, exhibition, gala, meeting, competition, trip, play), each with the approvals it needs judged from the 25 AUB rules only (`data/rulebook/aub-rules.json`, codes in `TASKS.md` T-08). Mark them synthetic. Save as `eval/synthetic-events.csv` with the same columns as the Running Club test set (Tatiana shares the header). Ask Tatiana when a rule is unclear; don't guess.
- Done when: 10 labelled events are in the repo, checked by Tatiana, ready for T-38's freeze.
- Progress (2026-10-31): ten synthetic rows added using the evaluation loader's columns and the sourced rulebook. Tatiana's label review and confirmation against the private D5 header remain before freeze.

- Verified (2026-11-16): Tatiana's checked/corrected ten synthetic rows are recorded in eval/FROZEN.md Freeze 2; the normalized file hash matches that freeze. Earlier pending-review note is superseded.

### J-15 Chatbot with sources (was T-17)
- Owner: joey
- Status: doing
- Needs: none
- What: Answer a cabinet member's question only from the club's approved facts and the AUB rules, following the frozen `ask` contract (`AskRequest` -> `Answer` in `src/clubops/contracts/knowhow.py`). Find candidate facts with the store's search (`KnowHowStore.search`), give them to the model, and check its answer in code: every citation must be one of the facts given; no facts found, or the model unsure, means `known: false` with who to ask (`ask`) and where to look (`look_in`), never a made-up answer (D-49). Redact the question before the model (`clubops.redaction`). Use the model client and its budget (`clubops.model`). Code in `src/clubops/chat/` (yours); wire it to `POST /api/chat/ask` in place of the placeholder (tell Tatiana). Develop with made-up facts and questions; Tatiana runs the real 42-question test (private) and tells you the score.
- Done when: the chatbot answers on the app with sources, says "not sure" with who to ask when it should, and Tatiana's 42-question run is recorded.
- Progress (2026-10-31): source-gated chat core and synthetic tests added. App endpoint wiring and Tatiana's private 42-question run remain pending.

### J-16 Secret scanning in CI (bonus)
- Owner: joey
- Status: blocked
- Needs: none
- What: GitHub's own secret scanning and CodeQL need a public repo or a paid plan, so run free equivalents in CI: gitleaks (secrets in the code and history) and a Python security linter. Fix or explain every finding.
- Done when: both run in CI on every PR and are green on `main`.
- Blocked (2026-11-10): `.github/workflows/` is outside Joey's assigned folders. Repo issue #84 asks Christophe to take CI ownership or identify its owner, then add pinned gitleaks and Bandit gates. Joey has not modified teammate-owned CI; the task remains open until both run green on PRs and `main`.

### J-17 Chatbot test runner
- Owner: joey
- Status: done
- Needs: J-15
- What: A script like `scripts/eval_plans.py` for the chatbot test (`chatbot-questions.csv`, frozen in T-04): ask each question, then score right answers, invented answers (an answer when the right reply is "not sure"), correct "not sure" replies, citations that really support the answer, and cost. Build and test it on synthetic questions; Tatiana runs it on the private file in T-26.
- Done when: `scripts/eval_chat.py` gives a result table on synthetic data, with tests, in replay mode.
- Progress (2026-10-31): replay-capable runner and synthetic scorer tests added. Tatiana's private CSV column mapping and recorded model responses still need verification.
- Progress (2026-11-10): focused synthetic scorer, CSV loader and replay CLI tests pass. Tatiana must confirm the frozen private header and recordings and run the private set; see issue #83. No private questions or answers are in Git.

- Verified (2026-11-16): synthetic replay runner and tests are present; the task's synthetic acceptance gate is complete. Private evaluation remains Tatiana's T-26 gate, not a claimed result.

### J-18 Poster
- Owner: joey
- Status: todo
- Needs: T-26
- What: Update the poster to the new scope (agent, learning, handover, web app) and to the final numbers from `results/` (every number points to `docs/evidence.md`). Tatiana checks the numbers.
- Done when: poster printed or submitted by 30 November.

### J-19 Proposal accuracy runner
- Owner: joey
- Status: done
- Needs: J-12
- What: Measure how close the proposal draft is to what the club really submitted: for each past event that has a real proposal (Tatiana gives the private files), compare the draft's answers field by field. Report correct, wrong, left for a person, and invented answers (filled in when the truth was unknown), plus form-check errors. Build and test it on synthetic proposals; Tatiana runs it on the real ones in T-26.
- Done when: `scripts/eval_proposals.py` gives a result table on synthetic data, with tests, in replay mode.
- Progress (2026-11-10): deterministic JSON-case runner and synthetic CLI tests pass. It prints counts and case IDs only. PR #80 is open with Tatiana requested for review; her private submitted proposals are used in T-26.

- Verified (2026-11-16): synthetic replay runner and tests are present; the task's synthetic acceptance gate is complete. Private evaluation remains Tatiana's T-26 gate, not a claimed result.

### J-20 New-club test and learning curve (D-91)
- Owner: joey
- Status: todo
- Needs: J-14, T-41
- What: Show ClubOps works for clubs it was not tuned on. `scripts/eval_new_club.py`: start a club empty (only the shared AUB layer), give it a starter pack of 0, 1, 3, then all onboarding documents, and plan its events after each step with `clubops.evaluation.plans` (approvals caught, false alarms, cost). Make 3 synthetic clubs of other kinds (academic, cultural, social; like J-14) with events and labels, and freeze them before running. Tatiana runs it on ASME (T-44) in T-26.
- Done when: the script gives a curve table per club on synthetic data, with tests, in replay mode.

### J-21 Automate shared-calendar cabinet access
- Owner: joey
- Status: review
- Needs: J-01
- What: Grant a named cabinet member read-only access to the club's shared Google calendar and revoke that rule when the member leaves. Keep Google access separate from ClubOps approval rights. Tatiana owns the cabinet API triggers and token storage; Christophe owns the Settings display. Do not change public, owner or manually elevated permissions automatically.
- Done when: fake-Google tests show repeat grants are safe, removal revokes only that member's reader rule, and a live cabinet-approved test verifies access after backend OAuth is connected.
- Progress (2026-11-10): reader ACL adapter and synthetic tests added. PR #79 is open with Tatiana and Christophe requested for review. Backend OAuth, cabinet add/remove triggers, Settings status, calendar ID and live test remain pending with their owners.
- Progress (2026-11-11): Tatiana's PR #79 review found the Running Club-only env placeholder. Replaced it with a private per-club JSON map, parser and synthetic multi-club/invalid-input tests. Joey must move the existing local ID into the new map privately. T-46 still owns backend loading and OAuth; live sharing remains pending.
### J-22 Inbox checks before any paid read (D-113, D-114)
- Owner: joey
- Status: review
- Needs: J-10
- What: Finishes J-10. In `src/clubops/inbox/`: an extra sending address per cabinet member, proven by a short code e-mailed to the club's `+tag` address and removed with the member; the original sender inside the forwarded text must be on the OSA list (passed in, never committed); skip e-mails already read; clean the text before the model (signatures, old replies, links, formatting); every skipped e-mail returns its reason; the same OSA e-mail sent to many clubs is read once. No model call in this task.
- Done when: synthetic tests cover unverified sender, wrong code, original sender not on the OSA list, duplicate, read-once across clubs, and an e-mail with instructions inside treated as data; each has a failure-matrix row. PR up by Thursday 12 Nov night; otherwise Tatiana takes it over.
- Progress (2026-11-12): Joey-owned `inbox.guards` and synthetic tests cover the verification code, private OSA allowlist input, skip reasons, content cleaning and cross-club fingerprint. API wiring and live Gmail acceptance remain with Tatiana's T-47; the guard does not make model calls or send mail.

### J-23 Deadline cards on the club calendar (D-116)
- Owner: joey
- Status: blocked
- Needs: J-02, T-48
- What: One calendar per club on `clubops.agent`. An approved deadline card with "Add to calendar" ticked creates an event with a reminder and invites only the people it names, through their Gmail. Event invites are set per event, cabinet by default. ClubOps never gets access to members' own calendars.
- Done when: synthetic tests (no live Google calls) and failure-matrix rows.

- Blocked (2026-11-16): T-48 is not merged and the frozen CalendarItem contract has no per-event invitee or deadline-card approval fields. Coordinate a standalone contract-change PR with Tatiana before implementing D-116; do not reuse the old role-calendar behavior as acceptance.
