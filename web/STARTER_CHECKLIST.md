# Start a club workspace

ClubOps starts with shared AUB know-how and learns your club from sources you
choose to provide. No member chat history is required. A president completes the
club interview first, then sees the four starter checks on the setup page.

1. **Check the cabinet.** Open the existing Cabinet settings to add members, return
   to setup, resume the finished interview and confirm you have checked the list.
   A failed or malformed cabinet response must be retried before confirmation.
2. **Add club rules or a constitution.** Select an authorized document, then press
   **Upload club rules for Review**. Selection alone makes no request.
3. **Add one past proposal.** Select an authorized example and explicitly upload
   it. Remove personal details according to the source's permission before upload.
4. **Check usual places and partners.** Review what the interview proposed. Skipped
   answers do not create facts. Use Chat to add missing context when you know it,
   then acknowledge what you checked, including anything still unknown.

Starter uploads accept nonempty TXT, MD, CSV, EML or XLSX files up to 2 MB in both
transports. Export a text version of a PDF first. An upload may use AI to propose
facts; those facts still need human Review. An accepted upload does not prove the
document is correct, complete, current or fully learned. Failures keep the selected
file for an explicit retry. A malformed success response never completes the tick.

## What the progress means

The four ticks are **browser-local metadata**, isolated by club, account and
demo/HTTP mode. Cabinet/context checks are the president's acknowledgements;
document checks record that this browser received an upload acknowledgement.
No source text, file name, member details, answers or raw file are saved in these
ticks. The application/server may separately retain approved uploads under its
normal private data policy. These checks are not approval decisions.

Resume checks the actual interview endpoint again after reload. The checklist does
not set `/me.club.setup_complete`, change server interview progress or infer that
all onboarding is complete. Another browser starts with no local ticks; recheck
them if your sources or cabinet change. When browser storage is unavailable, the
app's existing in-memory fallback lasts only for the current tab.

Purpose-specific checklist status is not in the current backend API. Durable
cross-device progress would need a separately agreed contract. The current UI
does not guess document purposes from names or claim server persistence.

## Integration and verification

Tatiana's merged #87 now wires the C-21 route and `/me` completion field. C-33 remains doing
until the deployed new-club flow and actual ASME onboarding are verified. This PR
changes only owned frontend files and shared evidence/task logs, not backend code
or contracts. No real source, paid call or deployed completion was invented.

Synthetic tests cover metadata isolation, strict response/file checks, explicit
uploads, rapid double clicks, 503/malformed response retries, cabinet actions,
reload, Review-only contents, accessibility and phone layout. Run browser suites
sequentially so their default Playwright result folders do not collide:

```sh
cd web
npm run check
npm run test:e2e -- setup.spec.ts
npm run test:e2e:http -- --grep starter
```

This branch is independent of C-34 / PR #75. Preserve both additive task/log/handoff
entries on merge. Use independent review and **Create a merge commit**.
