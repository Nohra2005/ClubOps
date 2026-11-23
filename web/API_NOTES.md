# Frontend API boundary

The supplied 22 October UI PDF is the source for `/api` paths and the example chat/run/task/approval field names. `src/api/types.ts` contains frontend view models, not replacement Python contracts. `VITE_API_MODE=demo|http` switches the transport. The demo persists synthetic data separately for each club; it never calls Google, a model, email or OSA.

The real transport uses authenticated cookies, encoded path identifiers, abortable requests, a bounded timeout and generic error messages by default. Only documented Restore 4xx refusals may supply a bounded plain explanation; all 5xx and unrelated actions retain generic errors. The backend must enforce authorization, CSRF protection, club isolation, content hashes and spend limits. Hiding a frontend button is not authorization.

## Current integration — 1 November 2026 (C-13 / C-19 / C-20)

The published [API table](../docs/api.md) now resolves the earlier T-22 questions.
The historical C-17 notes below describe the earlier contract review, not current blockers.

| Boundary        | Current handling                                                                                                                                                                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| HTTP convention | Bare UI views except canonical `AgentRun`; every changing request has `X-Requested-With: ClubOps`, including FormData and bodiless POSTs                                                                                                         |
| Google / logout | Official GIS button, `POST /auth/google {credential}`, HttpOnly session; protected `POST /auth/logout` must succeed before redirect. No token storage. Public client ID and real account test pending                                            |
| Planning        | Poll canonical run; questions are plain text; explicit `/continue` resumes the same ID and polling; leaving a limited run sends no invented stop action                                                                                          |
| Approval        | Revision sent to the server; local real-API test confirms no calendar items before approval and persistence after approval/reload. Approver IDs resolve through the cabinet list                                                                 |
| Chat            | Accept richer UI source objects and canonical citation IDs. Current server ask is an uncertainty placeholder until J-15; teaching is live, including no-fact results                                                                             |
| Handover        | Live C-19 deterministic endpoint; UI/export preserves all supplied sources and gap questions. Sign-off remains demo-only                                                                                                                         |
| Setup           | #55 service and #87 application wiring are merged. `POST /setup/next {answer?}` resumes or advances; `/me.club.setup_complete` reads saved progress. Local skip/resume HTTP tests use the actual app; Google/deployed acceptance remains pending |
| Usage           | Existing monthly planning totals plus recorded outcomes/cost-per-success; steps labelled accurately. Trace metrics remain unavailable until club-scoped traces are supplied                                                                      |
| Calendar        | Internal approved items work; Google sync is not connected in the API                                                                                                                                                                            |

Verified locally with real HTTP/SQLite on desktop and 375px phone: plan → approve →
calendar, handover, usage and cookie logout. Google SDK/credential behavior and failure
states use intercepted tests. See `VERIFICATION.md` for conditions and limitations.

T-18 teaching, after-event learning and uploads are now live. The UI accepts empty
review IDs without inventing a saved fact, shows instruction/outdated-source warnings,
and excludes flagged proposals from batch approval. HTTP uploads accept TXT, MD, CSV,
EML and XLSX up to 2 MB; the PDF/10 MB demo path is labelled separately.

Remaining server work: J-15 answers, J-07 draft wiring,
Google Calendar wiring, and uncontracted `__ui` actions.
These produce explicit unavailable responses; HTTP mode never saves them in demo storage.
C-13's deployed/every-screen completion criterion is still open.

For Tatiana: the assigned C-19 route calls the existing handover assembly then the new
view adapter; no frozen contracts changed. C-20 records only run metadata in the existing
save/finish callbacks (including continued runs) and extends `/usage`. Feature producers
can call `clubops.reports.traces.record_trace(data_dir, club_id, meta, status, error)`
with a known club context. The report never reads a global trace file, whose records lack
club ownership. Existing legacy monthly planning spend remains intact.

## HTTP session validation — 19 November 2026 (C-13)

Session boundary update (C-13, 19 November): the HTTP `/me` projection is validated
before protected UI renders. Member/club fields, declared roles, boolean setup flags
and nonnegative integer counts must match the published view. Invalid responses
show a generic recoverable connection error, without a default role or demo data.
An explicit retry performs another GET. Valid member and active roles remain
independent fields; no equality rule was added. Server authorization is unchanged.
See `src/api/session-response.ts` and `e2e/session-http.spec.ts`.

## Inbox capture and club-fact Restore — 19 November 2026 (C-35)

C-35 update (19 November): #95 ce1d514 and #96 8dccd0e document exact capture and
Restore responses. The HTTP Inbox now confirms each paid read separately, validates
`proposals`/`skipped` string arrays and requires a successful fresh metadata snapshot
after any unconfirmed outcome. No-fact success is acknowledged, not retried. HTTP
knowledge separates current/archive rows and offers Restore only to presidents on
expired club facts. A matching club/current acknowledgement triggers a fresh fact
read; disputed 409 text remains visible. No guessed proof/settings, expiry/calendar
payloads or shared Restore were added. See [INBOX_PREVIEW.md](INBOX_PREVIEW.md).

## Shared Review scope — 10 November 2026 (C-34)

T-41 / `tests/test_shared_layer.py` publish the `shared` field on Review cards and
the optional boolean `shared` on a decision. The frontend now preserves that field
independently of card type. Presidents can explicitly send true/false on individual
fact/merge/disagreement/rule decisions; ordinary cabinet decisions omit the override.
Shared proposals are excluded from batching, including when their type is `fact`.
Unsaved scope changes also require individual review. Source quotes on both sides
of comparisons are displayed as untrusted text; missing quotes are explicit.

The optional frontend field retains compatibility with older responses; legacy
type=rule stays restricted. The demo now follows the current single-president API
approval path rather than inventing a second-president requirement. Historical
waiting states remain display-compatible. Failed requests retain the draft/scope
choice for explicit retry. The API enforces authorization and prevents moving an
existing shared fact into a club; frontend controls do not replace those checks.

Tatiana: please add the already-supported `shared` fields to `docs/api.md` in your
next API documentation update. C-34 changes no backend code or frozen contracts.
See [REVIEW_GUIDE.md](REVIEW_GUIDE.md) and the synthetic HTTP tests for reproduction.

## Historical contracts 0.2.0 review — 23 October 2026 (C-17)

The frontend branch includes `main` through `597685d` (T-13). Published contracts and generated schemas were read as interfaces; backend implementation and contract definitions were not modified. `src/api/contract-responses.ts` translates fields consumed by the screens and rejects incompatible responses. Backend schema validation, authorization and the HTTP API remain server responsibilities.

| Published contract                                                              | Frontend handling                                                                                                                                                        | Still needed from T-22                                                                                                              |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `AgentRun.status`: `running`, `waiting_for_user`, `done`, `at_limit`, `failed`  | Map to existing screen states, preserving saved demo work; failed runs show a clear message                                                                              | Confirm HTTP run and answer response envelopes                                                                                      |
| Decimal costs, `cost_limit_usd`, step `tool` and `failed` state                 | Convert serialized costs, retain tool names and show the declared cost limit and failed steps                                                                            | Server enforcement of step/spend limits                                                                                             |
| A waiting run ends with a `question` step                                       | Derive the question input from that step; reject inconsistent runs and wrong run IDs                                                                                     | Structured detail confirmation and continue/stop endpoints                                                                          |
| `Answer.citations` contains `kh-…` item IDs                                     | Link actual IDs to knowledge pages; use the ID as its label until richer metadata is supplied                                                                            | Source labels/quotes and review IDs for disputed answers; currently link to the Review list                                         |
| Unknown `Answer.ask.role` and `look_in` can be null                             | Preserve the answer and who to ask; omit missing optional suggestions                                                                                                    | The contract allows `known=true, basis=none`; the UI rejects that contradictory support state rather than presenting it as verified |
| `Draft`: `draft_type`, `body`, `template_version`, `based_on`, `state=draft`    | Translate type/body; retain provenance; reject the wrong event/type and any sent state                                                                                   | Recipient/update time are not in this contract and are not fabricated; confirm nested event-detail and after-event draft envelopes  |
| Nullable calendar times, reminders, link, member ownership and cancelled status | Accept these fields, display member ownership and hide cancelled items                                                                                                   | Connection/sync metadata and task mutation IDs are HTTP view fields not supplied by `CalendarItems`                                 |
| Capability `Result[T]` envelope                                                 | Run, run-answer, ask and draft responses accept bare data or a Result envelope; degraded answers stay marked; HTTP-200 failures raise a generic error and preserve edits | Agree one HTTP response convention for all endpoints; a blocking result without usable run data is an explicit error                |

Draft names are translated explicitly. URL parameters still follow the supplied UI spec until Tatiana confirms them in T-22; capability enum values are not silently substituted into routes.

| Capability `draft_type` | Existing UI type / URL parameter |
| ----------------------- | -------------------------------- |
| `whatsapp_announcement` | `announcement`                   |
| `reminder_message`      | `reminder`                       |
| `sponsor_email`         | `sponsor_email`                  |
| `instagram_caption`     | `instagram`                      |
| `poster_text`           | `poster`                         |
| `expense_form`          | `expense`                        |
| `volunteer_shifts`      | `volunteers`                     |
| `impact_report`         | `impact_report`                  |

Other boundaries need an HTTP view model rather than a field rename:

- `EventRecord` is history (`on`, `spec_revision`, participants and outcome). It cannot supply the screen's schedule, venue, fields, approvals, tasks and proposal by itself. Event list/detail and nested run/draft responses still need the UI envelopes agreed in T-22.
- `Contact` has `contact_id`, `organization` and source references; it is not a `KnowHowItem`. Contacts, assets and document views need explicit server projections and cabinet-only access. No directory or asset endpoints were invented.
- Backend `Role` includes `member`; the cabinet session model remains limited to cabinet/adviser roles. T-22 must define ordinary-member access and the Google identity-to-actor mapping. Supporting a member as calendar owner does not grant cabinet access.
- Capability requests include `club_id`, `today`, `Untrusted` descriptions and wrapped draft instructions. UI endpoints accept the PDF's simpler inputs. The server must define how session context and input wrappers are supplied; the frontend does not impersonate an actor or call capabilities directly.

## Historical questions before T-22 (resolved or deferred in the current table above)

- The spec defines `GET /runs/{id}` but not detail-confirmation fields. The demo adds `question.kind=details`, `details` and `origins`; confirmation sends the edited object as the specified answer endpoint's `text` JSON string. The published `AgentRun` has no structured detail fields; Tatiana must agree the HTTP representation in T-22.
- Plan approval includes the revision being approved. The backend must bind approval to its exact content and reject stale revisions.
- At this historical review, event/review/calendar/knowledge/cabinet/setup shapes were fixtures. T-22 and #87 subsequently published/wired the current interfaces; see the current table and [CLUB_SETUP.md](CLUB_SETUP.md). This is no longer a blanket integration blocker.
- The task example contains a slash in `task_id`. The client URL-encodes identifiers; the backend router must support encoded IDs or agree another identifier.
- The spec does not supply endpoints for proposal-answer edits, approval-row status, draft text saves, pace leaders, feedback, knowledge edits/retirement, handover sign-off, Google OAuth, member role edits, stopping/continuing runs or sign-out. These use explicitly demo-only operations. The HTTP adapter returns an unavailable-action error instead of inventing a backend endpoint or silently writing locally.
- A new run after a limit needs explicit user confirmation. The demo starts another bounded run; it never silently extends the old run's 8-step / $0.05 allowance.
- Google login needs the backend's session/OAuth redirect and logout contracts. There are no frontend secrets or simulated authenticated production users.
- All authority and lead-time examples are synthetic and visibly marked as demo data. They must be replaced by verified, sourced backend records.

C-35 integration baseline (20 November): #95 Inbox and #96 Restore are now merged
in main `e4090c6`. Their exact documented responses still define this adapter;
remaining forwarding proof/settings and Review expiry/calendar shapes are not
inferred from those route merges. Synthetic frontend write checks are separate
from actual mailbox/provider/deployed acceptance. The preview-only role failure
is now F-238, preserving main's new adviser-route F-217.
