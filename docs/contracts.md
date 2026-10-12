# Interface contracts

The course brief asks application projects to define, for every interface between major components, its **schemas, validation, authentication and error behavior**. This page states the rules every contract follows. The per-capability table is generated: [capabilities.md](capabilities.md). The JSON Schemas are in [`schemas/`](../schemas).

## 1. Schemas and validation

- Every contract is a Pydantic model extending `Contract`: **strict** (unknown fields rejected), **immutable**, whitespace-trimmed.
- Invariants live in the model, so an invalid object cannot exist. Examples: a verified item names its verifier; a known `Answer` cites at least one item; a `HandoverEntry` cites an item or a gap; `RuleApplication` gives exactly one verdict per rule in its snapshot; a `ProposedAction`'s hash matches its payload.
- Identifiers have fixed shapes: clubs `running-club`, members `m-…`, events `ev-…`, know-how `kh-…`; times on forms are `HH:MM` (24-hour).
- Model output is validated against the same contracts before anything downstream sees it. A schema failure is `MALFORMED_MODEL_OUTPUT`, which is retried and never passed on.

## 2. The envelope

Every capability returns `Result[T]`:

| Field | Meaning |
|---|---|
| `status` | `ok` (data present), `needs_input` (at least one blocking question), `failed` (an error, no data) |
| `data` | The output contract `T` |
| `issues` | Findings about the data (e.g. a 12-hour time). Not failures of the call |
| `questions` | What only a human can answer |
| `error` | Present only when `failed` |
| `degraded` | True when the declared fallback produced the data |
| `trace` | Metadata only: capability and version, prompt version, model, latency, tokens, cost, retries |

Expected failures never cross a capability boundary as exceptions.

## 3. Authentication and authorization

- Every call carries an `Actor`: member, club, roles, and whether the member is authenticated with an AUB account.
- The runner refuses a request if any `club_id` in it, at any depth (e.g. `spec.club_id`), differs from the actor's club. A test requires every request type to name its club; `verify` is the one exception, and the store checks the club itself.
- Capabilities marked *cabinet only* refuse unauthenticated users and ordinary members.
- AUB-wide rules can only be verified by a club president.
- Executing an action requires an approval from an authenticated member of the same club holding one of the action's approver roles, for the exact payload, before it expires, once.

## 4. Error behavior

| Code | Recovery | Example |
|---|---|---|
| `invalid_input` | ask a human | malformed request |
| `ambiguous_input` | ask a human | two dates for one event |
| `not_found` | fail | verifying a proposal that no longer exists |
| `not_authorized` | refuse | member tries to verify; approver from another club |
| `stale_input` | fail | plan built on an old event revision; payload edited after approval |
| `conflict` | ask a human | item id already exists; action already executed |
| `upstream_timeout`, `upstream_error`, `rate_limited` | retry (backoff, per policy) | model API trouble |
| `malformed_model_output` | retry | output breaks the schema |
| `injection_suspected` | refuse | source tries to instruct the agent |
| `budget_exceeded` | fallback | per-packet spend limit reached |
| `internal` | fail | a bug |

The mapping is `ERROR_BEHAVIOR` in `contracts/common.py`; the runner applies it.

## 5. Untrusted input and provenance

- `Untrusted` wraps anything from outside: chats, emails, interviews, event descriptions. Only capabilities marked *takes untrusted input* accept it, and they can only produce proposals or drafts.
- Values carry an `Origin`: `stated`, `retrieved`, `computed`, `inferred`, `default`. **Inferred values always need a human check.** We use origin instead of a 0–1 confidence score because model-reported confidence is not calibrated.
- Know-how carries `Support` (how many sources and events back it) for the same reason.

## 6. Versioning and change process

- `SCHEMA_VERSION` (currently 0.1.0) covers all contracts; each capability also has its own version.
- **Frozen** capabilities change only through a PR labelled `contract-change` that bumps the version, regenerates schemas (`make schemas`), updates tests, and is reviewed by the contracts owner. **Provisional** ones may change freely until their phase starts.
- While on 0.x: a breaking change bumps the minor version; a compatible addition bumps the patch.
- CI fails if `schemas/` or `capabilities.md` do not match the code.
