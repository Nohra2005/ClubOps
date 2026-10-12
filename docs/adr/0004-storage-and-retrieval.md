# ADR 0004: Start with an in-memory store; add SQLite and full-text search next; embeddings only on evidence

**Status:** accepted · 2026-10-05

**Context.** One club's know-how is likely hundreds of items, not millions. A vector database added by default is hard to justify.

**Decision.** `KnowHowStore` is in memory for now and defines the methods every implementation keeps. Next: SQLite with FTS5 plus filters on kind, tags, scope and date. Embedding retrieval is added only if the surfacing and Q&A evaluations (D2, D3) show a measurable gain over full-text search.

**Consequences.** Fewer moving parts and a retrieval choice backed by data.
