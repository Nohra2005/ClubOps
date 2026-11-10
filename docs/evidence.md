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
| Five-minute presenter script and a reproducible synthetic UI rehearsal exist (demo preparation only) | [script](demo-script.md), [runner/commands](../web/demo/README.md), [301.56-second local proof](../web/demo/evidence/local-proof.json), inspected [question](../web/demo/evidence/question.png) and [warning](../web/demo/evidence/warning.png) frames; video stays in local output with a matching SHA-256 | actual silent synthetic take, six passing chapters, 10 Nov. No deployed/model/security/team-rehearsal claim; C-28 doing, final narrated backup pending |
