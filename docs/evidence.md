# Evidence ledger

Every claim made on the poster, in the proposal or in the final report, and the artifact that backs it.
**A claim without evidence is removed or reworded before submission.**

| Claim (where it appears) | Evidence needed | Status |
|---|---|---|
| "We interviewed 4 cabinets (Running Club, ACM, IISE, Math Society)" (poster) | Dated, consented interview notes in `research/interviews/` | needed |
| "All 4 had a submission sent back" (poster) | Same interview notes | needed |
| "One event took about 5 hours of paperwork" (poster) | Interview note or a timed walkthrough | needed |
| "12-hour times where 24-hour is required, and a date that disagreed with its description" (poster) | Redacted draft, plus F-01 / F-02 in the Failure Matrix | F-01 tested; redacted draft needed |
| "One prompt with no memory missed 31 of 51 required approvals (61%); with the OSA rulebook it missed 0" (poster) | The 20 event requests, labels, prompts and run logs in `eval/` | needed: re-run inside the repo |
| "Field-by-field audit of the proposal and Expense Form" (poster) | `data/forms/osa_event_proposal_2026_2027.json` (33 fields, each mapped to its source) | proposal form in place; Expense Form planned |
| Handover improves new officers' answers (planned headline result) | Three-way handover test in `eval/` | planned (Phase 3) |

## Paid model reads (spend log)

Every paid read gets a row **before** it runs (date, who ran it, what, cost). The provider dashboard is the final record; the app's own reads also appear in `/api/usage`. Amounts are estimates (about 1 cent per read) until checked against the dashboard.

| Date | Run by | What | Cost | Note |
|---|---|---|---|---|
| 2026-11-23 | Claude (assistant), on a scratch copy of the data | One read of the forwarded OSA e-mail "Campus Access Refinement" | about 0.01 USD | Not asked for and not logged at the time; Tatiana corrected it the same day |
| 2026-11-23 | Claude (assistant), on a scratch copy of the data | A second read, interrupted | 0 to 0.01 USD | Unconfirmed: check the provider dashboard |
| 2026-11-23 | Tatiana, in the app | Real read of the same e-mail (5 cards) | about 0.01 USD | Her own confirm click; also in `/api/usage` |
