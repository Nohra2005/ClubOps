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
