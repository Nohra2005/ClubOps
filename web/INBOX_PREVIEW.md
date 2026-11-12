# Inbox and deadline previews (C-35)

The demo build includes forwarding setup in **Setup** and **Settings**, a separate
**Inbox**, and a separate deadline lifecycle panel in **Review**. They use synthetic
messages and a reserved `.example` forwarding address. They make no HTTP, Google,
email or model calls. They do not publish knowledge, change the actual Review queue,
create calendar items or alter the server’s existing shared-approval policy.

C-35 remains doing: T-47 #92 adds a free fetch CLI, J-22 #93 adds checks, and neither
publishes the UI’s HTTP routes. T-48 and calendar-contract work remain with their
owners. D-115/D-116’s live policy changes are explicitly after ASME. The existing
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

In HTTP mode Inbox and forwarding show unavailable states; the lifecycle preview is
absent. They generate no real-looking address, request no guessed routes, extend no
Review payload and never fall back to a paid `/chat/teach` call. Settings’ existing
explicitly submitted manual notes are a separate action.

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
checks for unpublished requests/preview writes. These checks do not measure real
model quality, billing, security or deployment.
