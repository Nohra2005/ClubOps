# ADR 0005: One approval gate in front of every side effect

**Status:** accepted · 2026-10-05

**Decision.** Agents produce `ProposedAction`s. Execution is allowed only by `authorize_execution`: an authenticated member of the same club with an allowed role approved this exact payload (SHA-256) before expiry, and the idempotency key has not been used.

**Consequences.** An approved email cannot be altered afterwards, a retry cannot send twice, and the model never holds credentials. Approval burden (approvals and minutes per packet) is measured as a real-world constraint.
