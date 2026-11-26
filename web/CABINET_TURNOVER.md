# Cabinet turnover (C-39)

## Product flow

Turnover belongs in president Settings, once per cabinet term. Preparing a term
does not change today's cabinet. The president drafts its dates and incoming
officers, reviews inherited work and vacancies, then explicitly activates it.
Dates alone do not activate anything. Editing a reviewed draft requires review
again. Activation is a single transition, protected against stale or duplicate
submissions. Previous terms remain history.

Incoming officers receive one short introduction tied to their new term and
identity, with links to their inherited work and sourced role reference. Their
acknowledgment is not proof of training or agreement with every fact. Daily chat
has no recurring beginner switch, raw prompt preview or invisible question prefix.
Existing approved knowledge and its validity dates survive turnover. Tasks keep
their role assignments; history must continue to identify the original actors.

## Implemented boundary

The synthetic demo stores a complete lifecycle with its existing workspace:
draft, ready, activation, former cabinet, current term and officer acknowledgments.
It updates the synthetic cabinet in the same save as the term. Demo role switching
previews the new officer; it is not authentication. Browser storage is only a demo
store, with the existing tab-only fallback if persistence is unavailable.

HTTP mode removes the old tour and prompt machinery but cannot activate terms.
The published API has a read-only handover guide and individual cabinet edits,
not an atomic term transfer. No new HTTP route or role claim is guessed. The UI
does not transfer real permissions by sequential member requests or localStorage.
The proposed server contract below needs Tatiana's agreement before wiring.

## Contract request for Tatiana (proposal, not callable endpoints)

Please publish the HTTP operations and exact JSON for:

- Read current term, latest transition draft, permissions, revision and history.
- President-only create/update/cancel a draft: label, start/end dates, incoming
  officers and which current advisers remain. Return normalized values, stable
  IDs and explicit validation errors. At least one president must remain.
- Mark a specific revision reviewed. Any later edit invalidates that review.
  Define which outstanding work/knowledge changes invalidate the review too.
- Explicit activate with revision and idempotency token: atomically switch the
  active term and cabinet, archive the previous roster, preserve actor history,
  retain role-owned work and all knowledge validity metadata, invalidate outgoing
  sessions and refresh/reissue incoming sessions under server authority. Repeating
  an acknowledged request returns its original result; a different stale request
  returns 409. A failure must leave the previous cabinet usable.
- Per-member acknowledgment scoped to the authenticated identity and active term.
  `/me` needs agreed term/transition metadata; it must never trust a role, member
  ID or term supplied through a URL/browser preference as authorization.
- Invitation/acceptance: agree how incoming people authenticate before activation,
  whether their acceptance gates activation and how vacancies are handled. The
  demo does not claim that it sends real invitations or verifies another person.
- Define activation-date rules, overlapping terms, history access, cancellation,
  storage durability, stale review and recovery. The demo permits activation only
  during the drafted dates and after the previous term's end; no scheduled job.
- Expose server-confirmed active term and assigned role to retrieval/chat, with
  sources separating former practice from current rules. This is server context,
  not frontend-written system instructions or facts learned into club memory.

Owner split: Christophe for the web flow and owned handover views; Tatiana for
membership/session/term transaction and published contracts; chat owner for
server-confirmed term context. Cross-owner files are unchanged in this PR.

## Verification

Lifecycle unit/transport tests cover permission checks, validation, stale review,
double activation, two terms, history, unchanged work/knowledge and per-officer
acknowledgment. Browser tests exercise the synthetic full flow on desktop/phone
and the HTTP no-write boundary. None prove live identity transfer, invitations,
server durability, Google permissions or model tutoring quality.
