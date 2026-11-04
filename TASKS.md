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
- Needs: T-06, T-14, T-15, J-12, J-15, T-38, C-27, J-17, J-19
- What: Plan the held-out events with every baseline and with ClubOps (3 runs each, report the spread), plus ClubOps with an empty club memory (rules-only score) and the ASME events (D-50); automatic check against what really happened (approvals, proposal fields; no human graders, D-82); chatbot test; learning test; cost per successful plan. The measured real-world constraint (brief: "identify and evaluate at least one") is cost: run ClubOps with a cheap and a stronger model through OpenRouter and report quality, latency and cost per plan for each, so the model choice is a measured comparison. Commit sample traces (metadata only) in `traces/samples/`. Fix what it finds and turn each failure into a regression test.
- Done when: result tables in `results/` (including the cheap vs stronger model comparison), reproducible with `make eval`.

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

### C-14 Deploy the frontend
- Owner: christophe
- Status: todo
- Needs: C-13, C-18
- What: Deploy on the same free host as the backend.
- Done when: the cabinet opens the app from a link on their phones.
- Preparation: the shared Docker image and Caddy router are ready for a container build; see `web/DEPLOYMENT.md`. No deployed URL yet.

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
- Status: todo
- Needs: none
- What: The backend for the setup screen you built (C-11): `POST /api/setup/next {answer?}` walks a new club through about 10 questions (name, club or society and faculty, adviser, cabinet roles, signature events, usual venues, sponsors...) and turns each answer into a proposed fact in Review; the 25 AUB rules apply from day one (they are shared). Code in `src/clubops/api/setup.py` (yours); register it in place of the 501 route (one line; tell Tatiana). Tatiana gives you ASME's non-personal facts to seed ASME as the second club for the demo.
- Done when: a new club can go through setup in the demo, and ASME is the second club.

### C-22 Evaluation in CI (was T-30)
- Owner: christophe
- Status: todo
- Needs: T-26
- What: `make eval` runs from recorded model answers (no API keys) in the CI workflow and fails if a key number drops below its threshold (e.g. approvals missed, invented answers). Tatiana gives the thresholds with the T-26 results.
- Done when: the CI workflow runs `make eval` with regression gates.

### C-23 Frontend checks in CI (bonus)
- Owner: christophe
- Status: review
- Needs: none
- What: Add a CI job for `web/`: install from the lockfile, lint, type check, unit tests and a production build, so a broken screen fails the PR like broken Python does.
- Done when: the CI workflow runs the web job on every PR and it is green on `main`.
- PR #44: separate quality and synthetic browser/API jobs pass on GitHub; real BuildKit context checks are included. Main completion waits for reviewed merge.

### C-24 Docker Compose (bonus)
- Owner: christophe
- Status: review
- Needs: C-18
- What: A `docker-compose.yml` that starts the whole app locally (API + web, data on a volume, settings from `.env`) with one command, matching the deployed setup. Document it in the README.
- Done when: `docker compose up` on a fresh clone gives a working app with dev sign-in.
- PR #44: `docker compose up --build` starts the complete local app on loopback with a volume and synthetic cabinet account. Desktop/phone login and routing plus actual container replacement/data/session persistence verified. Dedicated CI gate added; public deployment remains C-18/C-14.

### C-25 OpenTelemetry traces (bonus)
- Owner: christophe
- Status: todo
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
- Status: todo
- Needs: none
- What: A script like `scripts/eval_plans.py` for the learning test (`learning-test.csv`, frozen in T-04): feed each source to the learning code (`src/clubops/learning/`), approve what it proposes, then ask the matching question and check the answer uses the new fact. Report facts learned, wrong facts, missed facts, cost. Build and test it on synthetic rows (`tests/factories.py`); Tatiana runs it on the private file in T-26.
- Done when: `scripts/eval_learning.py` gives a result table on synthetic data, with tests, in replay mode.

### C-28 Demo script and backup video
- Owner: christophe
- Status: todo
- Needs: C-14, C-18
- What: `docs/demo-script.md`: 5 minutes on the deployed app, showing what the brief asks: one normal plan, then edge cases (missing facts → the agent asks; the step limit; a hidden instruction in an uploaded document; a member without rights trying to approve). Seed a demo club with synthetic data only. Record a backup video in case the network fails on demo day.
- Done when: the script runs start to end on the deployed app, rehearsed once with the team, video saved.

### C-29 Keep the docs true (was T-31)
- Owner: christophe
- Status: doing
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
- Status: todo
- Needs: none
- What: A GitHub Projects board fed by `TASKS.md` (one card per task, columns = status), so ownership is visible on GitHub. One-week sprints (a Projects iteration per week with the tasks planned for it); a 10-minute review with the team each week, noted in one line under T-28.
- Done when: the board matches `TASKS.md` and 3 weekly sprints are recorded.

<!-- C-32 dropped on 2026-11-01 (D-82): no human graders, so no blind grading packets. -->


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
- Progress (2026-10-31): all eight draft types have a writer and synthetic tests. Approved private style examples and cabinet review are still needed to judge send-ready quality.

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

### J-13 Security tests (was T-24)
- Owner: joey
- Status: doing
- Needs: none
- What: An adversarial test set that tries to break ClubOps: instructions hidden in an event description or a forwarded e-mail ("ignore the rules", "approve this"), fake "OSA" rules sent as facts, one club reaching another club's data, the adviser or a non-cabinet account changing things, a forged sign-in, spending past the limits. Start with the planner and the API (live now); add the chatbot and learning when T-17 and T-18 land. Made-up data only. Tests in `tests/security/` (yours). Also update `docs/threat-model.md` and write the report sections on security, the calendar and the inbox.
- Done when: the set runs in `make check`; every way it found to break ClubOps has a failure-matrix row and is fixed (or the row says why not, and Tatiana agreed); and the injection attack success rate is measured (how many of the attacks worked) with the defences off and on, and reported in `results/`.
- Progress (2026-10-31): synthetic API, learning, planner prompt and budget boundary tests added. The full adversarial corpus, real defense-off/on measurement and report sections remain pending.

### J-14 Made-up events for the missing event types (was T-36)
- Owner: joey
- Status: review
- Needs: none
- What: 10 short, made-up event descriptions for types the Running Club never ran (workshop, conference, film screening, concert, exhibition, gala, meeting, competition, trip, play), each with the approvals it needs judged from the 25 AUB rules only (`data/rulebook/aub-rules.json`, codes in `TASKS.md` T-08). Mark them synthetic. Save as `eval/synthetic-events.csv` with the same columns as the Running Club test set (Tatiana shares the header). Ask Tatiana when a rule is unclear; don't guess.
- Done when: 10 labelled events are in the repo, checked by Tatiana, ready for T-38's freeze.
- Progress (2026-10-31): ten synthetic rows added using the evaluation loader's columns and the sourced rulebook. Tatiana's label review and confirmation against the private D5 header remain before freeze.

### J-15 Chatbot with sources (was T-17)
- Owner: joey
- Status: doing
- Needs: none
- What: Answer a cabinet member's question only from the club's approved facts and the AUB rules, following the frozen `ask` contract (`AskRequest` -> `Answer` in `src/clubops/contracts/knowhow.py`). Find candidate facts with the store's search (`KnowHowStore.search`), give them to the model, and check its answer in code: every citation must be one of the facts given; no facts found, or the model unsure, means `known: false` with who to ask (`ask`) and where to look (`look_in`), never a made-up answer (D-49). Redact the question before the model (`clubops.redaction`). Use the model client and its budget (`clubops.model`). Code in `src/clubops/chat/` (yours); wire it to `POST /api/chat/ask` in place of the placeholder (tell Tatiana). Develop with made-up facts and questions; Tatiana runs the real 42-question test (private) and tells you the score.
- Done when: the chatbot answers on the app with sources, says "not sure" with who to ask when it should, and Tatiana's 42-question run is recorded.
- Progress (2026-10-31): source-gated chat core and synthetic tests added. App endpoint wiring and Tatiana's private 42-question run remain pending.

### J-16 Secret scanning in CI (bonus)
- Owner: joey
- Status: todo
- Needs: none
- What: GitHub's own secret scanning and CodeQL need a public repo or a paid plan, so run free equivalents in CI: gitleaks (secrets in the code and history) and a Python security linter. Fix or explain every finding.
- Done when: both run in CI on every PR and are green on `main`.

### J-17 Chatbot test runner
- Owner: joey
- Status: doing
- Needs: J-15
- What: A script like `scripts/eval_plans.py` for the chatbot test (`chatbot-questions.csv`, frozen in T-04): ask each question, then score right answers, invented answers (an answer when the right reply is "not sure"), correct "not sure" replies, citations that really support the answer, and cost. Build and test it on synthetic questions; Tatiana runs it on the private file in T-26.
- Done when: `scripts/eval_chat.py` gives a result table on synthetic data, with tests, in replay mode.
- Progress (2026-10-31): replay-capable runner and synthetic scorer tests added. Tatiana's private CSV column mapping and recorded model responses still need verification.

### J-18 Poster
- Owner: joey
- Status: todo
- Needs: T-26
- What: Update the poster to the new scope (agent, learning, handover, web app) and to the final numbers from `results/` (every number points to `docs/evidence.md`). Tatiana checks the numbers.
- Done when: poster printed or submitted by 30 November.

### J-19 Proposal accuracy runner
- Owner: joey
- Status: todo
- Needs: J-12
- What: Measure how close the proposal draft is to what the club really submitted: for each past event that has a real proposal (Tatiana gives the private files), compare the draft's answers field by field. Report correct, wrong, left for a person, and invented answers (filled in when the truth was unknown), plus form-check errors. Build and test it on synthetic proposals; Tatiana runs it on the real ones in T-26.
- Done when: `scripts/eval_proposals.py` gives a result table on synthetic data, with tests, in replay mode.
