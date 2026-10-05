# ADR 0002: Nothing enters the knowledge base without a cabinet member

**Status:** accepted · 2026-10-05

**Context.** The knowledge base outlives every cabinet. A wrong or injected item would mislead every future team, silently.

**Decision.** The model can only create `KnowHowProposal`s. Only `verify`, a human-only capability, commits items. AUB-wide rules need a club president. Contradictions are decided by a person, and history is kept.

**Consequences.** Learning is slower but auditable; "the system learned it" always means "a named member confirmed it". Pending proposals feed the handover as open questions rather than being lost. Verification effort is a constraint we measure (approval burden).
