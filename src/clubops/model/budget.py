"""The per-plan limit (D-42): at most N model steps and $X per plan.

One ``Budget`` is created per plan (or per chat answer) and passed to every model call made
for it. The client checks it *before* calling the provider, so an over-limit plan never pays
for one more call. Replayed answers cost nothing but still count as steps, so tests exercise
the step limit exactly as live runs do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from clubops.capabilities.runner import CapabilityError, Usage
from clubops.contracts.common import ErrorCode


@dataclass
class Budget:
    max_usd: Decimal
    max_steps: int
    spent_usd: Decimal = field(default=Decimal("0"))
    steps: int = 0

    def check(self) -> None:
        """Raise before a call that would go past the limit."""
        if self.steps >= self.max_steps:
            raise CapabilityError(ErrorCode.BUDGET_EXCEEDED, f"step limit reached ({self.max_steps} model calls)")
        if self.spent_usd >= self.max_usd:
            raise CapabilityError(
                ErrorCode.BUDGET_EXCEEDED, f"cost limit reached (${self.spent_usd} of ${self.max_usd})"
            )

    def charge(self, usage: Usage) -> None:
        self.steps += 1
        self.spent_usd += usage.cost_usd

    @property
    def remaining_usd(self) -> Decimal:
        return max(Decimal("0"), self.max_usd - self.spent_usd)
