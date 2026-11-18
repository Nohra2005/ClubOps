# Inbox metadata and deadline previews (C-35)

The demo build includes forwarding setup in **Setup** and **Settings**, a separate
**Inbox**, and a separate deadline lifecycle panel in **Review**. They use synthetic
messages and a reserved `.example` forwarding address. They make no HTTP, Google,
email or model calls. They do not publish knowledge, change the actual Review queue,
create calendar items or alter the server’s existing shared-approval policy.

C-35 remains doing. Free fetch #92 and J-22's checks #93 are merged. Open #95
documents candidate waiting/skipped metadata routes and paid capture; open #96
documents club-fact Restore. This branch implements only the two metadata GETs in
HTTP mode. Paid/proof/settings/Restore response details and live acceptance remain
with their owners. D-115/D-116's live policy changes remain separate; the existing
Review controls and payloads are unchanged.

## Try it

```sh
cd web
npm ci
npm run dev
```

1. Open `/settings#forwarding`. Select a demo connection state; reader access is
   separate. Disconnected, pending, connected, expired and failed have distinct
   messages. The selector simulates responses; it is not an OAuth button.
2. Enter `member@example.com` and start sample verification. Typing alone proves
   nothing. Try a wrong code or simulate expiry; restart and use `DEMO-4821` to
   simulate receiving the code. Only sample domains are accepted here.
3. The Outlook guide describes forwarding OSA messages only, preserving original
   headers. Copying the example does not create a rule. Obtain the actual club +tag
   address from the operator/server and review the rule yourself in the live flow.
4. Test forwarding. Simulate receipt or failure; a passed delivery test makes no
   model call and approves no fact. Use **Open waiting email** to preserve this
   tab’s preview state while moving to Inbox.
5. Inbox’s two waiting samples already represent server-filtered mail; they are
   independent of the address-verification practice. Expand **Demo read outcomes**
   and choose partial failure. **Read waiting email · costs money** opens a separate
   confirmation; Cancel changes nothing. Confirm one success and one failure.
   Switch to success and retry only the failed message. Successful/skipped messages
   have no second read action. Facts are proposed, never approved.
6. In `/review`, use **Deadline lifecycle preview**. The calendar box starts ticked
   per C-35; whole cabinet is the default audience. Both choices can be changed.
   The sample date is fixed at 12 November. A past expiry archives the sample.
   Restore requires a new future date and the president role. AUB-wide publication
   is blocked pending the operator workflow; shared publication is never simulated
   as a real approval. Actual Review cards below remain separate.

Preview state lives in memory per API/session identity and resets on reload, role
or club change. No addresses, codes or message content go to browser storage.
Existing demo cabinet/knowledge fixtures retain their own storage independently.
Advisers browse without preview write controls. Cabinet members can practice their
own address verification and reads; connection changes and deadline/Restore actions
are president-only. These are UI guards, not proof of backend authorization.

## HTTP boundary for Tatiana

HTTP Inbox uses only `GET /api/inbox` and `GET /api/inbox/skipped`, with independent
loading, errors and explicit refresh. The parser accepts the documented bare arrays,
requires distinct nonempty string IDs and plain string subject/reason/explanation
fields, and drops extra fields such as bodies. Missing/null descriptive date or
forwarder labels display **Not supplied**, rather than implying verification or a
timestamp. This is a frontend projection policy, not a change to frozen contracts.

Adviser sessions do not mount either metadata resource. Server authorization is
still required. No metadata is copied to browser storage. Server strings render as
text, without HTML or automatic links. Failed, denied, malformed and uninstalled
routes show an error instead of an empty successful list or demo fallback. #95 is
not merged: current main can therefore return an unavailable/error response here.

Forwarding writes remain unavailable and the HTTP lifecycle preview is absent.
There is no paid-read control, guessed route, generated live address, extended
Review payload or paid `/chat/teach` fallback. Settings' explicitly submitted
manual notes are a separate action.

Please publish routes, exact JSON and role/error/retry rules for:

| Flow              | Information the UI needs                                                                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Connection        | Separate inbox/calendar status, president actions, reader access, expiry and reconnect/error text; never tokens or private calendar IDs |
| Verification      | Current member’s address state, server-issued code/expiry, observed proof, replacement/removal, permissions and failures                |
| Forwarding        | Server-supplied club +tag address, free test result and pending/timeout/error states                                                    |
| Queue             | Safe display metadata, allowed actions, skip-reason codes, pagination and freshness                                                     |
| Paid Read         | Explicit confirmation/cost information, proposal counts, idempotency, partial outcomes and which failed items may be retried            |
| Card lifecycle    | Authoritative expiry/archive state, shared/operator permissions, Restore payload and whether it returns to Review                       |
| Deadline calendar | Checkbox/audience fields, authorized recipients and separate calendar failure/retry after approval                                      |

`inbox/preview.ts` types are UI fixtures, not proposed frozen contracts. Replace the
fixture source with a validated adapter only after agreement. Google Testing-mode
reconnect is disclosed; expiry timing is not inferred in the browser. Never expose
private OSA allowlists, credentials or raw diagnostics. Real forwarding, permissions,
paid-read deduplication and calendar behavior need owner-side tests and approved
live acceptance.

## Published candidate interfaces: 16 November 2026

Tatiana has now documented candidate routes in open #95 and #96. The preview still
does not call them; publication of a route is separate from adapter integration and
live acceptance.

- #95: `GET /api/inbox` returns `[{id, subject, date, forwarded_by}]`, metadata only,
  without a model call. `POST /api/inbox/{id}/capture` is an explicit cabinet/CSRF
  paid read returning `{proposals: [review ids], skipped}`. Other-club IDs are 404,
  advisers are 403, and a failed read is 502 with the email retained for retry.
- Its 17 November update adds `GET /api/inbox/skipped` returning
  `[{id, subject, reason, why}]`, and 409 for a refused/already-claimed capture.
  The read-only view supports the two list routes; no capture request is made.
- #96: president/CSRF `POST /api/knowledge/{id}/restore {valid_to: date or null}`
  restores an expired fact as a new version. Not-expired facts are 409, past new
  dates are 422. Expired facts remain history and are omitted from planning.
  The updated route rejects AUB-wide Restore with 403 (operator only).
- Still needed for a strict adapter: concrete response examples/nullable field and
  `skipped` types, Restore's success response, J-22 skip/error/retry representation,
  and forwarding verification/proof/settings endpoints. A successful provider read
  is not inferred from a preview reducer state. No guessed routes or fallback paid
  teaching calls are permitted.

D-127 is the preview decision; D-128 covers this read-only HTTP projection.
F-228/F-229 cover proof and paid-read guards; F-230 is the HTTP write boundary and
F-231 covers read-only metadata failures/privacy. The original D-124/F-214/F-215
and later F-216 numbers collided with #95/#96 and were renumbered. Earlier handoff
entries retain their historical IDs.

## Reproduce synthetic checks

Run browser suites sequentially; they share their default artifact directory.

```sh
cd web
npm run check
npx playwright test inbox.spec.ts settings.spec.ts setup.spec.ts review.spec.ts shell.spec.ts
npm run test:e2e:http
```

Unit cases cover proof/expiry, sample-only addresses, free versus paid transitions,
partial retries/deduplication, roles and expiry/Restore/shared-publication guards.
Browser cases cover confirmation/Cancel, retries, connection states, adviser controls,
storage isolation, desktop/phone layout and accessibility. The HTTP regression
checks the documented metadata GETs, unavailable writes and independent failures.
These checks do not measure real
model quality, billing, security or deployment.
