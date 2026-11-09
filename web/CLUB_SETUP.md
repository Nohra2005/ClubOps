# New-club setup (C-21)

The owned service/router is in `src/clubops/api/setup.py`. The screen uses the
existing `POST /api/setup/next {answer?}` response fields: `question`, `index`,
`total`, `done`, `rules_count`. Empty requests resume; `[skip]` advances without
extraction. No request changes cabinet accounts, renames a club or approves memory.

**Integration is pending in PR #55.** Main's application still registers the 501
placeholder and reports `setup_complete: true`. The new module is tested through
an explicit integration adapter; this is not evidence that the production route
has already been replaced. Tatiana was notified in coordination issue #43.

## API owner wiring

Create one `SetupService(config.data_dir)` and include its `router(...)` in place
of the placeholder, supplying these public callbacks:

| Argument                   | Required behavior                                                                                                                                                                                                                                                                                                                          |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `actor_dependency`         | Return the authenticated session's `Actor`. Never accept a club or actor from the body. The router independently requires a verified president and the CSRF header.                                                                                                                                                                        |
| `capture(request)`         | Call the public learner's **capture**, not learn/auto-submit. Each explicit answer has one shared budget of at most eight steps / $0.05. Use the existing configured model/redaction/tracing path; record usage only with known club context. Return `CaptureResult`; surface operational failures rather than silently declaring success. |
| `submit(proposal)`         | Put the exact proposal into Review, idempotently by proposal ID. Never verify it. Idempotence must also respect earlier approval/rejection if a user decided the Review card before resuming a failed response; do not resurrect a decided proposal.                                                                                       |
| `rules_count(club_id, on)` | Count current approved AUB-scope **rules**, not club facts or pending proposals. The date is calculated in Asia/Beirut. Shared rules are read, never cloned or invented during setup.                                                                                                                                                      |
| `clock()`                  | Return an aware datetime, using the application's existing clock.                                                                                                                                                                                                                                                                          |

Wire `/api/me.club.setup_complete` to `service.complete(member.club_id)`. Missing
progress means incomplete; decide explicitly whether any existing club should be
migrated as already complete. Do not infer completion from unapproved knowledge.
The service has no member/profile mutation interface.

`tests/test_setup_endpoint.py` is the executable reference adapter: it reuses the
registered authentication dependency through public FastAPI metadata, replaces the
placeholder **only in the test app**, and connects actual SQLite Review/shared-rule
storage with synthetic extraction. It checks club isolation and a partial queue
failure before any Review decision. It is not an application-wiring patch or a
real-model quality test. The production submit callback's decided-card idempotence
still needs owner review.

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

## Second-club demo and remaining work

The frontend's ASME workspace is visibly synthetic. Both HTTP adapter tests use
synthetic accounts and facts. Tatiana must provide/seed the actual non-personal ASME
facts with sources and human approval; no real ASME facts were invented or committed.
The approved shared rulebook applies from the start without approving setup answers.

After owner wiring: repeat setup on a new authenticated club, reload mid-flow,
complete with skips, inspect pending Review cards, approve one explicitly and check
that only that club can retrieve it. Recheck `/me`, persistence across restart and
the actual ASME demo. C-21 stays open until this is verified.

## Verification

```sh
uv run pytest tests/test_setup.py tests/test_setup_endpoint.py
cd web
npm run test:e2e -- setup.spec.ts
npm run test:e2e:http -- --grep setup
```

On Windows, run the schema generator with Python UTF-8 mode (`python -X utf8
scripts/export_schemas.py --check`); its generated Markdown contains Unicode. A
locale-decoding mismatch is not a reason to regenerate or edit the frozen contracts.
