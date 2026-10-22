# Frontend API boundary

The supplied 22 October UI PDF is the source for `/api` paths and the example chat/run/task/approval field names. `src/api/types.ts` contains frontend view models, not replacement Python contracts. `VITE_API_MODE=demo|http` switches the transport. The demo persists synthetic data separately for each club; it never calls Google, a model, email or OSA.

The real transport uses authenticated cookies, encoded path identifiers, abortable requests, a bounded timeout and generic error messages. The backend must enforce authorization, CSRF protection, club isolation, content hashes and spend limits. Hiding a frontend button is not authorization.

## Clarifications required before C-13

- The spec defines `GET /runs/{id}` but not detail-confirmation fields. The demo adds `question.kind=details`, `details` and `origins`; confirmation sends the edited object as the specified answer endpoint's `text` JSON string. Tatiana must confirm this representation in T-13.
- Plan approval includes the revision being approved. The backend must bind approval to its exact content and reject stale revisions.
- Event summary/detail envelopes, review card variants, calendar/knowledge envelopes, cabinet mutation identifiers and setup response fields are frontend fixtures pending backend agreement.
- The task example contains a slash in `task_id`. The client URL-encodes identifiers; the backend router must support encoded IDs or agree another identifier.
- The spec does not supply endpoints for proposal-answer edits, approval-row status, draft text saves, pace leaders, feedback, knowledge edits/retirement, handover sign-off, Google OAuth, member role edits, stopping/continuing runs or sign-out. These use explicitly demo-only operations. The HTTP adapter returns an unavailable-action error instead of inventing a backend endpoint or silently writing locally.
- A new run after a limit needs explicit user confirmation. The demo starts another bounded run; it never silently extends the old run's 8-step / $0.05 allowance.
- Google login needs the backend's session/OAuth redirect and logout contracts. There are no frontend secrets or simulated authenticated production users.
- All authority and lead-time examples are synthetic and visibly marked as demo data. They must be replaced by verified, sourced backend records.
