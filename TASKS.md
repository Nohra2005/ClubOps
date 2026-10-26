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
- Tatiana's evaluation data (T-01 to T-05) is **frozen before** the planner (T-14) and chatbot (T-17) are built. Otherwise the test can be tuned to the system.
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
- Done when: `eval/FROZEN.md` is committed, before any code for T-14 or T-17.

### T-05 Line up the 3 graders and the grading sheet
- Owner: tatiana
- Status: todo
- Needs: none
- What: Ask 3 cabinet members outside the team (e.g. Gaëlle, Marc, Alexandra). Make a grading sheet: each part of a plan scored 1–5 (approvals, deadlines, proposal, budget, messages), with what each score means.
- Done when: 3 people said yes and the sheet exists.

### T-06 Baseline prompts
- Owner: tatiana
- Status: todo
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
- Status: todo
- Needs: T-12, T-18
- What: Teach ClubOps the club's main tips, contacts and sponsors (president notes; old-chat import only if time allows).
- Done when: Knowledge shows the club's core facts, approved.

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

### T-16 Proposal draft
- Owner: tatiana
- Status: todo
- Needs: T-14
- What: Fill the OSA proposal form (33 questions) with origin and source per answer; 24-hour times; dates consistent with the description.
- Done when: drafts for the test events pass the form checks.

### T-17 Chatbot with sources
- Owner: tatiana
- Status: todo
- Needs: T-04, T-10, T-12, T-13
- What: Answer only from approved facts, with sources. When unsure: "not sure", who to ask, where to look. Never invent a rule.
- Done when: runs on the 30-question test.

### T-18 Learning inputs and the approval gate
- Owner: tatiana
- Status: todo
- Needs: T-11, T-12
- What: Turn chat teaching, the after-event form, forwarded OSA emails and uploaded documents (including past expense forms, kept as a price list) into proposed facts; merge repeats; detect contradictions; flag outdated documents. Nothing is saved until approved in Review.
- Done when: each input type produces Review cards; approve / reject / merge work.

<!-- T-19 moved to C-19 on 2026-10-24: it fits Christophe's part and lightens Tatiana's load. -->
### T-20 New-club setup and ASME
- Owner: tatiana
- Status: todo
- Needs: T-18
- What: The setup chat for a new club (about 10 questions) and ASME seeded as the second club.
- Done when: ASME can go through setup in the demo.

<!-- T-21 moved to J-11 on 2026-10-24: it fits Joey's part and lightens Tatiana's load. -->
### T-22 Backend API for the UI
- Owner: tatiana
- Status: review
- Needs: T-13
- What: Every endpoint in the UI spec's API table, same field names; sign-in (decide the method with Christophe, see C-01).
- Done when: Christophe can switch from fake data to the real API (C-13).
- Progress (2026-10-24): part 1 live (sign-in, events, runs, approve, tasks, calendar, knowledge, review, cabinet, usage); see `docs/api.md`. Part 2 (drafts, after-event, teach, handover, documents, setup) answers 501 until those tasks are built.

<!-- T-23 moved to C-20 on 2026-10-24: it fits Christophe's part and lightens Tatiana's load. -->
### T-24 Security tests
- Owner: tatiana
- Status: todo
- Needs: T-17, T-18
- What: Injection attempts, fake "OSA" rules, unauthorized actions; each failure gets a Failure Matrix row and a test.
- Done when: the adversarial set runs in `make check` or `make eval`.

<!-- T-25 moved to C-18 on 2026-10-24: it fits Christophe's part and lightens Tatiana's load. -->
### T-26 Run the final evaluation
- Owner: tatiana
- Status: todo
- Needs: T-05, T-06, T-14, T-15, T-16, T-17, T-38
- What: Plan the held-out events with every baseline and with ClubOps (3 runs each, report the spread), plus ClubOps with an empty club memory (rules-only score) and the ASME events (D-50); automatic check against what really happened; blind 1–5 grading by the 3 graders; chatbot test; learning test; cost per successful plan. Fix what it finds and turn each failure into a regression test.
- Done when: result tables in `results/`, reproducible with `make eval`.

### T-27 Poster, demo and report
- Owner: tatiana
- Status: todo
- Needs: T-26
- What: Update the poster so every number matches the new results (`docs/evidence.md`); demo script; final report from the design log.
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

### T-30 Evaluation in CI
- Owner: tatiana
- Status: todo
- Needs: T-26
- What: `make eval` runs from recorded responses (no API keys) in CI and fails if a key number drops below its threshold (e.g. approvals missed, invented answers).
- Done when: the CI workflow runs `make eval` with regression gates.

### T-31 Keep the docs true
- Owner: tatiana
- Status: todo
- Needs: T-22
- What: Update `docs/architecture.md`, `docs/threat-model.md`, `docs/data-provenance.md`, `docs/knowledge-base.md`, `docs/rubric-map.md` and the README to the new scope (agent loop, calendar, email intake, web app, deployment). Setup must work from a fresh clone in one command.
- Done when: a teammate sets the project up from the README alone.

### T-32 Real pilot event
- Owner: tatiana
- Status: todo
- Needs: C-18, C-14
- What: Plan one real Running Club event in November with ClubOps on the deployed app. Record the cabinet's time, what ClubOps caught or missed, and their feedback.
- Done when: a short pilot write-up in `results/`, used in the report and poster.

### T-33 Handover test (decide: keep or drop)
- Owner: tatiana
- Status: todo
- Needs: C-19
- What: The planned headline result: new officers answer 10 standard questions with old chats only vs. the handover pack. Decide by 8 November whether there is time; if dropped, remove the claim from `docs/evidence.md`.
- Done when: either run with results in `results/`, or dropped and recorded in the design log.

### T-34 Make the repo easy to grade
- Owner: tatiana
- Status: todo
- Needs: T-27, T-30, T-31
- What: The grader is likely an AI agent reading the repo. Add a "How to grade this project" section at the top of the README: each rubric item → the file that proves it → the command that reproduces it (see `docs/plan.md`). Then have a fresh AI session, with no context, grade the repo against the rubric and fix every gap it finds.
- Done when: a fresh-session review finds no rubric item without evidence.

### T-35 ASME data (real second club)
- Owner: tatiana
- Status: doing
- Needs: none
- What: Ask Alexis (ASME president) for 3-5 past proposals (ideally a workshop, trip or conference), what each really needed, his OK to use them privately, and a 10-minute setup chat later. Remove phone numbers and IDs.
- Done when: ASME events and their real approvals are in the private eval folder.
- Progress (2026-10-23): Alexis sent 4 proposals (screen recordings) and 12 expense forms. 15 ASME events drafted privately in `clubops-raw/eval/asme-events.csv` with guessed approvals; personal details removed. Left: Alexis fills the real approvals (column `approvals_real`) and confirms the open questions in `notes`.

### T-36 One made-up event per missing event type
- Owner: tatiana
- Status: todo
- Needs: T-35
- What: 10 short event descriptions for types the Running Club never ran (workshop, conference, film screening, concert, exhibition, gala, meeting, competition, trip, play). Label each one's approvals from the OSA documents only. Mark them synthetic.
- Done when: 10 labelled events saved privately and included in T-04's freeze.

### T-37 Other presidents' questions
- Owner: tatiana
- Status: done
- Needs: none
- What: Take the real questions from the presidents' group, reword them with no names (D-51), write the correct answer or "not sure, ask X" from OSA staff replies and documents.
- Done when: added to the chatbot test before T-04's freeze.

### T-38 Freeze the other-club test sets
- Owner: tatiana
- Status: todo
- Needs: T-35, T-36
- What: Same as T-04 for the ASME events and the made-up events: held-out split, hashes in `eval/FROZEN.md` (Freeze 2).
- Done when: Freeze 2 is filled in, before the generalization run in T-26.


### T-39 Create the ClubOps Gmail inbox
- Owner: tatiana
- Status: todo
- Needs: none
- What: Create one Gmail account for ClubOps (the service, not one club), e.g. clubops.inbox@gmail.com, owned by the team. Turn on 2-step verification. Give Joey access for J-10. Its password and tokens live only in a password manager and the host's settings, never in the repo.
- Done when: the account exists and Joey can open it.
---

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

### C-14 Deploy the frontend
- Owner: christophe
- Status: todo
- Needs: C-13, C-18
- What: Deploy on the same free host as the backend.
- Done when: the cabinet opens the app from a link on their phones.

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
- Status: todo
- Needs: none
- What: Put the backend (`uvicorn clubops.api.app:build --factory`) on the same free host as the frontend (Render, D-47), with a persistent disk for `CLUBOPS_DATA_DIR` and the secrets from `.env.example` in the host's settings, never in the repo. Load the rulebook and add the president (`scripts/load_rulebook.py`, `scripts/add_member.py`). Deployment files (`render.yaml`, `Dockerfile`) are yours; ask Tatiana before changing Python code.
- Done when: the cabinet signs in on the deployed app and plans an event.

### C-19 Handover endpoint (was T-19)
- Owner: christophe
- Status: todo
- Needs: none
- What: Serve the Handover screen from the club's approved facts. The assembly already exists in `src/clubops/knowhow/handover.py` (plain code, no AI); write `src/clubops/api/handover.py` that turns its `HandoverPack` into the screen's `HandoverGuide` (sections, entries with sources, gaps with who to ask and where to look) and register it in `api/app.py` in place of the 501 route (one line; tell Tatiana). Synthetic data in tests.
- Done when: `GET /api/handover/{role}` returns the guide for each role, with tests for an empty club and a club with gaps.

### C-20 Cost and trace report (was T-23)
- Owner: christophe
- Status: todo
- Needs: none
- What: Cost, tokens, latency, retries and failures per feature from the traces (`clubops.tracing`, metadata only) and the agent runs; cost per successful plan. A script writes the report to `results/`; `GET /api/usage` shows the real numbers per feature for the Settings screen. Code in `src/clubops/reports/` (yours) plus the usage route (tell Tatiana).
- Done when: the report in `results/` and the Settings numbers come from real runs.
---

## Joey: calendar, reminders, drafts

### J-01 Read the calendar contract and set up Google
- Owner: joey
- Status: blocked
- Needs: none
- What: Read `docs/calendar-contract.md`. Create the Google Cloud project, turn on the Calendar API, create the shared club calendar. Secrets never go in the repo.
- Done when: a test item appears in the shared calendar from your code.
- Blocked: OAuth client, club calendar IDs and a cabinet-approved live test are not available yet. The adapter and setup steps are in `src/clubops/calendar/README.md`.

### J-02 Sync calendar items
- Owner: joey
- Status: doing
- Needs: J-01, T-13
- What: Create, move (same ID, new date), and delete items so Google always matches ClubOps. ClubOps is the boss; edits in Google are overwritten. Only approved plans are sent.
- Done when: tests show no duplicates when an item is sent twice or moved.

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
- Status: doing
- Needs: J-02
- What: Task done stops its reminders; event cancelled deletes all its items.
- Done when: tested.

### J-06 Calendar tests and failure rows
- Owner: joey
- Status: doing
- Needs: J-05
- What: Tests with a fake Google (no real calls in `make check`); a Failure Matrix row for each failure mode (Google down, item sent twice, role with no person).
- Done when: `make check` passes with your tests.

### J-07 Draft templates
- Owner: joey
- Status: doing
- Needs: none
- What: Templates for: WhatsApp announcement, reminder message, sponsor email, Instagram caption, poster text (never logos), expense form, volunteer shifts, impact report. Match the club's real style (look at past announcements).
- Done when: each template produces a draft a cabinet member would send without edits.

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
- Status: todo
- Needs: T-39, T-18
- What: Read the ClubOps inbox (Gmail API) and turn each forwarded e-mail into input for learning. One inbox for all clubs: each club forwards to its own address with a "+" tag (`clubops.inbox+running-club@gmail.com`), and the tag says the club. Drop e-mails whose sender is not on that club's cabinet list, and e-mails with an unknown tag. Pass the rest as `Untrusted` text (sender, date, subject, body; attachments listed by name only) to T-18's capture step, so every fact waits in Review. Never auto-approve; never reply to the sender. Code in `src/clubops/inbox/`.
- Done when: forwarding a real OSA e-mail puts a proposed fact in that club's Review, and tests (with made-up e-mails) cover: wrong tag, sender not on the list, the same e-mail twice (no duplicate), and an e-mail with instructions inside ("ignore the rules...") treated as data. Each case has a failure-matrix row.

### J-11 Daily check and OSA rule check (was T-21)
- Owner: joey
- Status: todo
- Needs: J-04
- What: A daily plain-code check of each club's upcoming events (overdue tasks, deadlines inside 2 days, plans outdated by edits) that calls the AI only when it finds a real problem; and the monthly OSA website check from September until the president marks the new rules as in (D-30, D-31). Both run on a schedule on the server and write reminders, never send messages. Code in `src/clubops/checks/`.
- Done when: both run on a schedule on the deployed app, with tests (made-up events) and failure-matrix rows.
