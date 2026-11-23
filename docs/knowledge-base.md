# Knowledge base and working memory

Updated 16 November 2026. The memory model separates proposed knowledge, verified knowledge and event/run working state. Public interfaces are in `src/clubops/contracts/`; availability is in `docs/api.md`, with the merged #87 setup integration explained in [CLUB_SETUP.md](../web/CLUB_SETUP.md).

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

A source is untrusted input. Learning extracts source-supported candidates and submits proposals. Existing knowledge can lead to a create, merge, update or contradiction proposal; a model cannot verify its own output. Human decisions create the verified view, while retired, superseded, expired and unapproved items stay out of current knowledge.

Under D-95, extraction must identify how long a fact holds and whether it is stated
as fact/agreement or opinion/suggestion/question. One-time arrangements and personal
views are dropped; this-term facts have an expiry. The model supplies these labels,
so the filter is not proof that every surviving fact is correct. A cut-off/unreadable
model response is a failed source, not an off-topic source; retry it rather than
mark it learned (D-98/F-168).

Reviewers must inspect the existing fact beside a proposed replacement. F-171 records
a real wrong-match limit: accepting an unrelated replacement could retire useful
knowledge. Quote checks do not prove that two statements concern the same rule.
For shared AUB facts, approval/sharing requires a president and replacements retain
the shared layer (D-91/F-163).

Instruction warnings and old-document flags are visible in Review and excluded from bulk approval. They remain available for an individual source check. Official status cannot be acquired merely by uploading a document or typing an instruction into a chat.

Handover entries retain every current approved source. Unsupported entries become gaps naming a question, who to ask and where to look; they do not become fabricated rules. The chatbot's production implementation is separate J-15 work and is still a placeholder on main at this update.

## Examples and authority

Know-how kinds include procedures, lessons, relationships, gotchas, decisions, identity, rhythm, obligations and shared rules. A synthetic operational example is: "The example supplier prefers a confirmation call." It is test data, not an AUB policy. Real lead times and submission requirements must come from the sourced rulebook or authorized verified club knowledge; none are inferred from these examples.

## Authentication and credentials

Production Google identity is matched to the cabinet list, with an HttpOnly session cookie. Session club/role authorizes reads and decisions. Provider keys remain server-side. Local Compose has a separate explicit development target and volume-backed random signing secret; the default production image rejects local-login builds and insecure development cookie settings.

## Known limits

Missing model-token/latency/retry records appear as unavailable, not zero. The optional
C-25 OTLP exporter and synthetic local Jaeger proof are implemented; real producer
hooks, real-provider measurements and deployed alerts remain separate work. See
[observability/README.md](../web/observability/README.md) for the export boundary.
Production retention/backup recovery and evidence that handover improves users'
results remain unverified. Read-only screen visits do not silently launch a model
run or verify knowledge. The accepted answer-only setup stale-tab limit (F-151)
and rejected-proposal reappearance after a partial queue failure (F-201) still apply;
use one setup tab and inspect proposals before approving them.
