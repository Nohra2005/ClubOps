"""The event planner as an agent run (D-42): the steps it chose, the question it is waiting on,
and how much of its limits it used. The UI's agent steps panel shows exactly this."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from clubops.contracts.common import ClubId, Contract, EventId, Slug, Untrusted


class RunStatus(StrEnum):
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"  # the last step is a question
    DONE = "done"
    AT_LIMIT = "at_limit"  # stopped at 8 steps or the cost limit; the user may continue or stop
    FAILED = "failed"


class StepState(StrEnum):
    RUNNING = "running"
    DONE = "done"
    QUESTION = "question"
    FAILED = "failed"


class AgentStep(Contract):
    n: int = Field(ge=1)
    tool: Slug = Field(description="what the agent chose to do, e.g. 'search-memory', 'apply-rules', 'ask-user'")
    text: str = Field(max_length=200, description="one plain line for the steps panel")
    state: StepState


class PlanEventRequest(Contract):
    club_id: ClubId
    description: Untrusted = Field(description="the cabinet member's own words about the event")
    today: date
    event_id: EventId | None = Field(default=None, description="set when re-planning an existing event")
    answer: str | None = Field(default=None, max_length=1000, description="the user's reply to the agent's question")


class AgentRun(Contract):
    run_id: Slug
    club_id: ClubId
    event_id: EventId | None = None
    status: RunStatus
    steps: list[AgentStep]
    steps_used: int = Field(ge=0)
    step_limit: int = Field(ge=1)
    cost_usd: Decimal = Field(ge=0)
    cost_limit_usd: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if [s.n for s in self.steps] != list(range(1, len(self.steps) + 1)):
            raise ValueError("steps are numbered 1..n in order")
        if self.steps_used > self.step_limit:
            raise ValueError("steps_used cannot exceed step_limit")
        waiting = bool(self.steps) and self.steps[-1].state is StepState.QUESTION
        if (self.status is RunStatus.WAITING_FOR_USER) != waiting:
            raise ValueError("a run waits for the user exactly when its last step is a question")
        if self.status is RunStatus.DONE and self.event_id is None:
            raise ValueError("a finished run names the event it planned")
        return self
