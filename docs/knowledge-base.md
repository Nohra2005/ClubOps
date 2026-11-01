# Knowledge base and working memory

Updated 1 November 2026. The memory model separates proposed knowledge, verified knowledge and event/run working state. Public interfaces are in `src/clubops/contracts/`; availability is in `docs/api.md`.

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

No automatic raw-data, history, recording or trace purge is claimed. Retention/deletion and backup restoration still require an implemented operational policy and evidence; see [data-provenance.md](data-provenance.md).

## Knowledge lifecycle

A source is untrusted input. Learning extracts source-supported candidates and submits proposals. Existing knowledge can lead to a create, merge, update or contradiction proposal; a model cannot verify its own output. Human decisions create the verified view, while retired, superseded, expired and unapproved items stay out of current knowledge.

Instruction warnings and old-document flags are visible in Review and excluded from bulk approval. They remain available for an individual source check. Official status cannot be acquired merely by uploading a document or typing an instruction into a chat.

Handover entries retain every current approved source. Unsupported entries become gaps naming a question, who to ask and where to look; they do not become fabricated rules. The chatbot's production implementation is separate J-15 work and is still a placeholder on main at this update.

## Examples and authority

Know-how kinds include procedures, lessons, relationships, gotchas, decisions, identity, rhythm, obligations and shared rules. A synthetic operational example is: "The example supplier prefers a confirmation call." It is test data, not an AUB policy. Real lead times and submission requirements must come from the sourced rulebook or authorized verified club knowledge; none are inferred from these examples.

## Authentication and credentials

Production Google identity is matched to the cabinet list, with an HttpOnly session cookie. Session club/role authorizes reads and decisions. Provider keys remain server-side. Local Compose has a separate explicit development target and volume-backed random signing secret; the default production image rejects local-login builds and insecure development cookie settings.

## Known limits

Missing model-token/latency/retry records appear as unavailable, not zero. Real provider measurements, OpenTelemetry export, deployed alerts, production retention/backup recovery and evidence that handover improves users' results remain separate tasks. Read-only screen visits do not silently launch a model run or verify knowledge.
