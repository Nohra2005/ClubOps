# Inbox, archive and Restore (C-35)

Updated 19 November 2026 against the exact candidate API responses published by
Tatiana in #95 (ce1d514) and #96 (8dccd0e). Those PRs remain under review. C-35 stays
doing: forwarding proof/settings and Review expiry/calendar payloads plus actual
deployed/mailbox acceptance remain open. No backend implementation or frozen
contract is changed by this frontend work.

## HTTP Inbox

`GET /api/inbox` and `GET /api/inbox/skipped` are metadata-only. Waiting/skipped
lists have independent errors and explicit refresh. Render server strings as text,
drop extra body fields and keep metadata out of browser storage. Date/forwarder
labels are documented strings that can be empty; Not supplied is the display for
missing descriptive values. Adviser sessions do not mount either resource.

Each waiting message has a separate Read this control and cost confirmation.
Cancel, typing and browsing make no capture request. Confirm sends only the
encoded message ID to `POST /api/inbox/{id}/capture`, with cookies and CSRF header.
There is no price estimate and no automatic paid retry. The synchronous action lock
prevents rapid duplicate submissions; only one read is active from this page.

The response has `proposals: string[]` and `skipped: string[]`. Show the number of
unique Review card IDs without approving them. Empty arrays are a completed no-fact
result, not a failure; skipped reasons are plain text. Mixed/repeated IDs are not
rejected by an invented contract constraint. Acknowledged messages cannot be read
again from this page even if a stale metadata response still lists them.

An HTTP error, timeout or malformed result leaves the outcome unconfirmed. The
message is blocked until a successful fresh waiting-list response arrives; clicking
Refresh alone or receiving a failed refresh does not unlock a paid retry. Check
Review and explicitly confirm any new attempt. The server remains responsible for
read-once claims, cross-club isolation, queue/review persistence and billing. No
exactly-once billing or durable browser recovery is claimed.

## HTTP knowledge archive and Restore

Current knowledge and Archive filter the existing category/search response locally;
no archive endpoint or extra paid request is invented. Non-current records stay
available for reference. Tatiana clarified that `may_be_outdated` means the end date
passed, not a source warning. Retired records are also non-current, but not eligible
for Restore.

Offer Restore only in HTTP mode to a president viewing a club-scoped fact with
`status: may_be_outdated`. Shared AUB facts have no Restore control; ask the operator
about updating them. A disputed expired fact can look eligible and still receive a
409, so preserve and display the documented server explanation.

The confirmation shows the statement and requires a new date (today or later in
Beirut) or an explicit No end date choice. It sends
`POST /api/knowledge/{id}/restore {valid_to: date or null}`. Verify the returned
item ID, club scope and current state, then reload the existing fact view; do not
render an unvalidated POST projection as the new fact. This is the person's approval
of a new current version, not a new learned fact or a model call.

Only Restore's documented 403/404/409/422 errors may supply a bounded plain `detail`
sentence. Render it as text. Other actions and all server 5xx responses retain the
generic transport errors. A timeout/malformed acknowledgement requires Reload fact
before another attempt; no automatic POST occurs. Ordinary 4xx refusals preserve
the chosen date for correction.

## Separate synthetic demo

The demo build retains forwarding practice in Setup/Settings, a sample Inbox and a
separate deadline lifecycle panel in Review. All addresses/messages/codes are
synthetic (`.example`); state stays in memory for this API/session identity and
resets on reload/account change. It sends no HTTP, Google, email, model or calendar
request and does not alter the real Review queue or approval policy.

In the demo, try a wrong/expired proof, a failed forwarding test, simulated partial
read and retry, then deadline expiry/archive/Restore. Connection selectors simulate
states, not OAuth. Shared publication remains blocked in the preview. Actual HTTP
forwarding proof/settings and Review expiry/calendar choices are still unavailable
until their exact routes and payloads are published. Existing manual notes in
Settings are a separate explicit action, never an Inbox fallback.

## Reproduce

Run browser suites sequentially because they share their default artifact directory.

```sh
cd web
npm run check
npm run test:e2e:http
npx playwright test inbox.spec.ts settings.spec.ts setup.spec.ts review.spec.ts shell.spec.ts
```

Unit/browsers exercise confirmation/Cancel, rapid clicks, no-fact/skipped results,
failed refresh, ambiguity, scope/role guards, date/no-end approval, public error text,
wrong acknowledgement, source storage separation, phone layout and accessibility.
HTTP tests intercept synthetic responses. They establish frontend behavior, not a
real mailbox/provider/security measurement or completed ASME onboarding. The
existing live-API suite is separate and does not exercise unmerged Inbox/Restore
routes. Exact source-contract refs and dated results are in VERIFICATION.md.

Decisions: D-127/D-128 (preview/read-only), D-131 (confirmed documented writes).
Failures: F-217/F-218/F-228/F-229 (preview), F-231/F-232 (metadata/write boundary),
F-235/F-236 (paid-read and Restore). Earlier log IDs and dated evidence are history.
