# Reviewing knowledge

Shared knowledge is visible to all AUB clubs; club knowledge stays with your club.
Only a president chooses sharing and approves shared knowledge; check the source, then confirm the decision.

## Review one proposal

Disagreements appear first. Compare both statements and their quoted sources before
choosing a decision. A missing quote is explicitly identified; inspect the original
source instead of treating a title or model statement as evidence. Quotes are
untrusted text, including text that looks like instructions or HTML.

A president can use **Share with all AUB clubs** on an individual fact, merge or
disagreement. Toggling it does not save anything or call AI. The choice is sent as
`shared: true/false` only when the president confirms a decision. Existing shared
knowledge cannot be pulled into one club: the server enforces that boundary.
Other cabinet members can review club knowledge; advisers remain read-only.

If a decision fails, edits and the sharing choice stay on the page for an explicit
retry. Check the error rather than assuming anything was approved. No source or
proposal becomes verified merely because it is displayed here.

## Batch approval

**Approve all facts** includes only pending, unflagged club facts with no unsaved
sharing choice. Shared knowledge, disagreements, merges, rules, warned/outdated
sources and already-decided cards require individual review. Batch requests do not
silently change a fact's scope. The server remains the authorization boundary.

## Verification and limits

C-34 uses the existing `shared` field and decision parameter specified in TASKS.md
and exercised by `tests/test_shared_layer.py`. No backend implementation or shared
contract is changed. The demo follows the current single-president approval path;
historical `waiting_second_president` responses remain display-compatible.

`web/src/api/review-policy.test.ts` checks role, batch and ordering boundaries.
`web/e2e/contracts.spec.ts` exercises the actual frontend HTTP adapter with synthetic
responses on desktop/phone, including a denied request and unchanged draft retry.
`web/e2e/review.spec.ts` checks the persistent synthetic demo. These are regression
checks, not evidence of deployment or real reviewer acceptance. Production setup
wiring and new-club pilot verification remain separate tasks.
