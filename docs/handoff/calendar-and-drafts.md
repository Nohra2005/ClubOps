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
