# Knowledge base (memory)

The brief asks each memory to define its **scope, lifetime, retrieval strategy and privacy**. ClubOps has one long-lived memory, the club's know-how, plus short-lived working state.

## What counts as know-how

| Kind | Example (synthetic) |
|---|---|
| Procedure | Booking Green Field: reservation form, then calendar invite; three weeks ahead |
| Lesson | Early-morning runs drew more people than evening runs |
| Relationship | A local supplier gives water; prefers WhatsApp; wants its logo on the bib |
| Gotcha | OSA sends forms back if times are not in 24-hour format |
| Decision | Entry fees were dropped because attendance fell (what and why) |
| Identity | Tone, audience, signature events, values |
| Rhythm | What happens in which month each year |
| Obligation | Semester report to OSA, membership minimum |
| Rule (AUB-wide) | Non-AUB guests require approval |

## Stores

| Store | Scope | Lifetime | Retrieval | Privacy |
|---|---|---|---|---|
| **Verified know-how** | One club, or AUB-wide for rules | Until retired or superseded; old versions kept as history | Filters on kind, tags, scope, validity date; full-text search (planned); embeddings only if evaluation shows a gain ([ADR 0004](adr/0004-storage-and-retrieval.md)) | Cabinet-only by default. Contacts stored as references, never raw numbers. Quotes capped at 500 characters |
| **Pending proposals** | One club | Until verified or rejected | By club, op, target item | Same as above; shown as open questions, never as facts |
| **Raw sources** (chat exports, emails, interview notes) | One club | Processed, then deleted; never committed to the repo | Not retrieved; only the extracted know-how and short quotes remain | Personal data redacted before capture; consent recorded per source ([data-provenance.md](data-provenance.md)) |
| **Requester details** (AUB ID, phone) | One request | The duration of one draft | Not retrieved | Held as secrets; never stored, logged or traced |
| **Handover packs** | One club and role | Kept per signed version | By role and date | Cabinet-only |
| **Traces** | System | 90 days (planned) | By trace id, capability | Metadata only; no request or response content |

## Lifecycle of an item

`proposed → verified → (merged into · updated by · contradicted by) → superseded` or `retired`. Only `verified` items inside their validity window are **current**. Everything else is history or an open question.
