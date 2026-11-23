# New-club setup (C-21)

Setup questions are now the primary onboarding path, as Tatiana confirmed through
Christophe on 9 November. WhatsApp history import has been dropped for onboarding:
members have not consented to those messages being read, and clubs need a path
that does not require handing over chats. Ask the president for organizational
facts directly, then review extracted proposals. This team decision is in D-103;
Tatiana is taking the broader privacy question to the professor. No professor
approval or third-party consent is inferred here.

The owned service/router is in `src/clubops/api/setup.py`. The screen uses the
existing `POST /api/setup/next {answer?}` response fields: `question`, `index`,
`total`, `done`, `rules_count`. Empty requests resume; `[skip]` advances without
extraction. No request changes cabinet accounts, renames a club or approves memory.

**The service and application wiring are merged:** #55 supplies the owned module;
[#87](https://github.com/Nohra2005/ClubOps/pull/87) replaces the placeholder and wires
`/me.club.setup_complete` to saved progress. The older setup 501/always-true notes in
`docs/api.md` predate that merge. Local browser verification now uses the actual
application factory over HTTP, real session cookies and SQLite, without replacing
the setup route. This is distinct from deployed/Google/ASME acceptance.

## Maintainer integration boundary

The wiring introduced in #87 connects `SetupService(config.data_dir)` and its
`router(...)` using these public callbacks. Keep these requirements when maintaining
the integration:

| Argument                   | Required behavior                                                                                                                                                                                                                                                                                                                          |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `actor_dependency`         | Return the authenticated session's `Actor`. Never accept a club or actor from the body. The router independently requires a verified president and the CSRF header.                                                                                                                                                                        |
| `capture(request)`         | Call the public learner's **capture**, not learn/auto-submit. Each explicit answer has one shared budget of at most eight steps / $0.05. Use the existing configured model/redaction/tracing path; record usage only with known club context. Return `CaptureResult`; surface operational failures rather than silently declaring success. |
| `submit(proposal)`         | Put the exact proposal into Review, idempotently by proposal ID. Never verify it. Idempotence must also respect earlier approval/rejection if a user decided the Review card before resuming a failed response; do not resurrect a decided proposal.                                                                                       |
| `rules_count(club_id, on)` | Count current approved AUB-scope **rules**, not club facts or pending proposals. The date is calculated in Asia/Beirut. Shared rules are read, never cloned or invented during setup.                                                                                                                                                      |
| `clock()`                  | Return an aware datetime, using the application's existing clock.                                                                                                                                                                                                                                                                          |

`/api/me.club.setup_complete` reads `service.complete(member.club_id)`. Missing
progress means incomplete; decide explicitly whether any existing club should be
migrated as already complete. Do not infer completion from unapproved knowledge.
The service has no member/profile mutation interface.

`tests/test_setup_endpoint.py` is the executable reference adapter: it reuses the
registered authentication dependency through public FastAPI metadata, replaces the
placeholder **only in the test app**, and connects actual SQLite Review/shared-rule
storage with synthetic extraction. It checks club isolation and a partial queue
failure before any Review decision. It is not an application-wiring patch or a
real-model quality test. The production submit callback's decided-card idempotence
has a known limit: F-201 documents reappearance of a rejected proposal after a partial
queue failure. Nothing is approved automatically; this is not a solved retry guarantee.

## Progress, retry and data

Progress lives at `<data-dir>/setup/<validated-club-id>.sqlite3`, so it follows the
existing persistent data volume. The row holds the next question and, while a queue
operation is incomplete, the exact extracted proposals plus an answer fingerprint.
The outbox is committed before queue submission. Resume retries those same IDs
without another extraction; changing the answer while that retry is outstanding
returns 409. Once queued, active progress fields no longer retain the proposal copy.
This is not a promise of secure deletion from SQLite pages, backups or storage.

Model/extraction failure leaves the question unchanged. A returned `sources_failed`
also rejects the whole result before any partial facts are queued (F-174); retry the
answer explicitly. Off-topic results with no failures may still advance normally.
The screen keeps the draft
and offers an explicit resume action. Skips, typing and ordinary resume do not call
a model. All source text is `Untrusted`, tagged as an interview/setup question; the
learner must apply the usual redaction/injection safeguards. Questions ask for roles,
departments and organizational facts, not personal contact details or private links.
Real application state and any outbox copies stay out of Git, logs and screenshots.

An answer-only request has no question token. A delayed response retry or second tab
can therefore answer a later question accidentally after the first request completed.
Use one setup tab. In #43, Tatiana declined the question-token/If-Match extension:
setup is president-only and one-time, and she accepts the documented two-tab limit.
No HTTP-contract extension is planned for this task.
F-151 and `test_answer_only_contract_reproduces_the_unresolved_stale_tab_limit`
preserve an explicit reproduction. A passing reproduction test is not a claim that
stale answers are rejected. Keep the reproduction while the accepted limit exists.

## ASME onboarding and remaining work

The frontend's ASME workspace is visibly synthetic. Both HTTP adapter tests use
synthetic accounts and facts. Tatiana must provide/seed the actual non-personal ASME
facts with sources and human approval; no real ASME facts were invented or committed.
The approved shared rulebook applies from the start without approving setup answers.

The local no-interception regression covers a fresh synthetic president club,
redirect, skip, stop/reload/resume, unchanged progress after missing CSRF, completion,
`/me`, empty Review and adviser denial on desktop and phone. Separate empty clubs
isolate each browser's durable progress. It deliberately skips extraction: it is
not a model-quality, proposed-fact approval or live-provider test.

Still verify on the deployed service: Google sign-in, a sourced answer's pending
Review card, explicit approval, cross-club retrieval denial, restart persistence and
actual authorized ASME onboarding. C-21 stays open until this acceptance is recorded.
Interview completion and browser-local starter checklist completion are separate.

## Verification

```sh
uv run pytest tests/test_setup.py tests/test_setup_endpoint.py
cd web
npm run test:e2e -- setup.spec.ts
npm run test:e2e:http -- --grep setup
npm run test:e2e:live -- setup-live.spec.ts
```

Main includes #89's explicit UTF-8 file handling for Windows. Older checkouts can
run the schema generator with Python UTF-8 mode (`python -X utf8
scripts/export_schemas.py --check`). A locale-decoding mismatch is not a reason to
regenerate or edit the frozen contracts.
