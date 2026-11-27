# Knowledge base and working memory

Updated 26 November 2026 against main `4722838` and the published API/design decisions. The memory model separates proposed knowledge, verified knowledge and event/run working state. Public interfaces are in `src/clubops/contracts/`; availability is in `docs/api.md`, with the merged #87 setup integration explained in [CLUB_SETUP.md](../web/CLUB_SETUP.md).

## Stores, scope and lifetime

| Store | Scope and lifetime | Retrieval and privacy |
|---|---|---|
| Verified know-how | Shared AUB rules or one club; current while verified and within its validity window. Old versions remain history until an explicit retention decision | SQLite/full-text search plus kind, tag and validity filters. No embeddings are currently required. Club access comes from the session |
| Pending proposals | One club; remain pending until a person verifies/rejects/edits them | Review queue with source, proposed change, known alternative, instruction warning and outdated flag. Not treated as verified answers |
| Contacts, assets and event history | Club-scoped operational records; separate from a free-form conversation | Access through published contracts/API views. Authorized contact details can exist privately; they must not appear in public fixtures, traces or model prompts |
| Event specifications and runs | One club and revision/run ID; saved so the UI can poll and reload | Facts, steps, budget and questions support the current workflow. Runtime data may be sensitive. In-process background execution does not promise restart recovery |
| Handover guide | Computed for one club, role and current knowledge view | Deterministic assembly plus all current citations and explicit gaps. Production sign-off/version retention is not yet wired; the demo sign-off is synthetic |
| Model recordings | Private replay/record material under configured storage | Replay avoids paid calls; recordings may contain derived content and are not metadata-only. Keep them private and subject to source authorization |
| Run and trace reports | Per-club metadata; month aggregation uses Beirut time for recorded metrics | Deduplicate cumulative snapshots/trace IDs. No prompt, answer or step text in report records. Unscoped global traces are not read into a club's report |
| Browser demo | Synthetic workspace, isolated by club and test user | Browser storage only for the demo; it is not production authentication or approved club knowledge |
| Setup interview | Durable per-club SQLite progress and temporary extraction outbox; registered by #87 | Explicit president answers are untrusted inputs and only propose knowledge. Resume/skips do not extract. Completing the interview does not approve a fact or finish the starter checklist |
| Starter checklist | Browser-local acknowledgements scoped by mode, club and member | Boolean ticks only; a successful upload acknowledgement is not fact verification. No cross-device checklist persistence is claimed |

No automatic raw-data, history, recording or trace purge is claimed. Retention/deletion and backup restoration still require an implemented operational policy and evidence; see [data-provenance.md](data-provenance.md).

## Knowledge lifecycle

A source is untrusted input. Learning extracts source-supported candidates. Interview answers, chats and uploaded documents submit proposals for a person to check. The trusted OSA mail exception is narrower: after the published paid-read action and intake/source checks, plain code may apply a clean new fact; a change to existing knowledge (update or merge), a contradiction or flagged mail waits in Review (D-138 narrowed by D-151, merged #150). The model does not grant authority. Applied facts retain history with Edit/Undo; retired, superseded, expired and unapproved items stay out of current retrieval. Background scheduling is not established by this API path.

Under D-95, extraction must identify how long a fact holds and whether it is stated
as fact/agreement or opinion/suggestion/question. One-time arrangements are excluded from lasting Knowledge, and personal
views are dropped; this-term facts have an expiry. Quoted, dated deadlines from
clean trusted OSA mail have a separate calendar-task path (D-150, #146); they
do not become permanent know-how. The model supplies these labels,
so the filter is not proof that every surviving fact is correct. A cut-off/unreadable
model response is a failed source, not an off-topic source; retry it rather than
mark it learned (D-98/F-168).

Reviewers must inspect the existing fact beside a proposed replacement. F-171 records
a real wrong-match limit: accepting an unrelated replacement could retire useful
knowledge. Quote checks do not prove that two statements concern the same rule.
For shared AUB facts, approval/sharing requires a president and replacements retain
the shared layer (D-91/F-163).

Instruction warnings and old-document flags are visible in Review and excluded from bulk approval. They remain available for an individual source check. Official status cannot be acquired merely by uploading a document or typing an instruction into a chat.

Handover entries retain every current approved source. Unsupported entries become gaps naming a question, who to ask and where to look; they do not become fabricated rules. The cabinet chat route now uses J-15's source-gated core for the authenticated club (#149, D-200). Source labels include expiry or No end date, and inactive facts are filtered. This is merged API wiring, not measured provider answer quality, a cross-device tutor or verified deployed acceptance. The owner's API table still contains a historical placeholder note; #149/D-200 supersede that availability note.

## Examples and authority

Know-how kinds include procedures, lessons, relationships, gotchas, decisions, identity, rhythm, obligations and shared rules. A synthetic operational example is: "The example supplier prefers a confirmation call." It is test data, not an AUB policy. Real lead times and submission requirements must come from the sourced rulebook or authorized verified club knowledge; none are inferred from these examples.

## Authentication and credentials

Production Google identity is matched to the cabinet list, with an HttpOnly session cookie. Session club/role authorizes reads and decisions. Provider keys remain server-side. Local Compose has a separate explicit development target and volume-backed random signing secret; the default production image rejects local-login builds and insecure development cookie settings.

Signing in does not also connect Google Calendar or the shared Gmail inbox.
The merged #160/#161 APIs and #167 controls expose separate connection states:
presidents manage their club calendar, operators manage the Gmail connection and
cabinet members can Fetch without starting the paid model read. Browser callback
messages are notices; the status GET is the source for connection state. Encrypted
refresh credentials stay in private server storage (D-155/D-156), outside knowledge
and metadata reports. Neither Google connection changes a member's ClubOps role.

Cabinet turnover must eventually update server term, membership and session context
atomically. Open [#170](https://github.com/Nohra2005/ClubOps/pull/170) demonstrates
the proposed once-per-term flow and incoming brief with synthetic local state;
it is not in this main baseline. The server contract remains with Tatiana in
[#169](https://github.com/Nohra2005/ClubOps/issues/169). Browser acknowledgements
cannot activate a production cabinet or change what the live chatbot remembers.

## Known limits

Missing model-token/latency/retry records appear as unavailable, not zero. The optional
C-25 OTLP exporter and synthetic local Jaeger proof are implemented; real producer
hooks, real-provider measurements and deployed alerts remain separate work. See
[observability/README.md](../web/observability/README.md) for the export boundary.
Production retention/backup recovery and evidence that handover improves users'
results remain unverified. Read-only screen visits do not silently launch a model
run or verify knowledge. The accepted answer-only setup stale-tab limit (F-151)
still applies; use one setup tab. Rejected-card persistence was addressed in
#142; that does not prove all interrupted capture/queue failure paths recover.
Inspect proposed changes before approving them.

## Expiry and evaluation interfaces

Review and Knowledge carry `valid_to` as an ISO date or null. Review decisions
can set it or explicitly clear it with an empty string; absent preserves the
suggestion (#135/#136). The published Knowledge Edit contract currently carries
text and optional lead_time_days, so changing expiry after approval still needs
an API extension. Restore is a separate president-only expired-club-fact action.
Web follow-up #152 covers full-year/detail/comparison labels, source-check hints
and unsaved metadata protection; it merged as 62d1787 after all five checks passed.

The learning quality sheet (C-27, D-87) and chatbot quality sheet (D-152, #151)
are human-marked private artifacts. Their offline score commands count ratings;
exact text matching is not evidence of semantic answer correctness. The published
[chatbot evaluation](../results/chatbot-evaluation.md) reports 41 scored questions
from the 42-question set, excluding Q18, with one president marking one model run.
It used a separate evaluation store enriched with president-stated facts, not the
live club store. Its 13 correct, one partly correct and 16 missed answerable
questions show both useful answers and limited coverage under those conditions;
they do not establish universal correctness or an evaluated turnover tutor.
