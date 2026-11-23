"""Shared building blocks used by every contract.

Rules that apply to every capability (see docs/contracts.md):

* Every capability takes one request model and returns ``Result[T]``.
* Expected failures are returned as ``Result(status=FAILED, error=...)``; they never
  cross a capability boundary as exceptions.
* Every request names the ``Actor`` making it; authorization is checked against it.
* Anything that came from outside the system (chats, emails, interviews) arrives
  wrapped in ``Untrusted`` and is treated as data, never as instructions.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, Literal, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCHEMA_VERSION = "0.3.0"

# --------------------------------------------------------------------------- ids

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")]
ClubId = Slug
MemberId = Annotated[str, StringConstraints(pattern=r"^m-[a-z0-9-]{2,63}$")]
EventId = Annotated[str, StringConstraints(pattern=r"^ev-[a-z0-9-]{2,63}$")]
ItemId = Annotated[str, StringConstraints(pattern=r"^kh-[a-z0-9-]{2,63}$")]
Time24 = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
FieldPath = Annotated[str, StringConstraints(pattern=r"^[a-z_][a-z0-9_.\[\]]*$")]


class Contract(BaseModel):
    """Base class: strict, immutable, no unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


# ------------------------------------------------------------------------ actors


class Role(StrEnum):
    PRESIDENT = "president"
    VICE_PRESIDENT = "vice_president"
    SECRETARY = "secretary"
    TREASURER = "treasurer"
    EVENTS = "events"
    SPONSORSHIP = "sponsorship"
    COMMUNICATIONS = "communications"
    MEMBER = "member"
    ADVISER = "adviser"


CABINET_ROLES: frozenset[Role] = frozenset(
    {
        Role.PRESIDENT,
        Role.VICE_PRESIDENT,
        Role.SECRETARY,
        Role.TREASURER,
        Role.EVENTS,
        Role.SPONSORSHIP,
        Role.COMMUNICATIONS,
    }
)


class Actor(Contract):
    """Who is making a request. ``verified`` means authenticated with an AUB account."""

    member_id: MemberId
    club_id: ClubId
    roles: frozenset[Role]
    verified: bool

    @property
    def is_cabinet(self) -> bool:
        return self.verified and bool(self.roles & CABINET_ROLES)


# ----------------------------------------------------------------------- sources


class SourceKind(StrEnum):
    CHAT_MESSAGE = "chat_message"
    EMAIL = "email"
    RETROSPECTIVE = "retrospective"
    INTERVIEW = "interview"
    EVENT_LOG = "event_log"
    FORM = "form"
    DOCUMENT = "document"
    USER_INPUT = "user_input"


class SourceRef(Contract):
    """Points at the exact place a fact came from."""

    kind: SourceKind
    source_id: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    locator: str | None = Field(default=None, max_length=200, description="message id, line range, page")
    quote: str | None = Field(default=None, max_length=500, description="verbatim supporting text")
    observed_at: datetime


class Untrusted(Contract):
    """Content from outside the system. Must be treated as data, never as instructions."""

    content: str = Field(max_length=20_000)
    source: SourceRef

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()


class Origin(StrEnum):
    """Where a value came from. ``INFERRED`` values must be checked by a human."""

    STATED = "stated"  # a person said it in the input
    RETRIEVED = "retrieved"  # read from verified know-how or the club profile
    COMPUTED = "computed"  # derived by deterministic code
    INFERRED = "inferred"  # guessed by a model
    DEFAULT = "default"  # club default, nobody confirmed it for this case


class Money(Contract):
    amount: Decimal = Field(ge=0, decimal_places=2)
    currency: Literal["USD", "LBP"] = "USD"


# ------------------------------------------------------------------------ errors


class ErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    AMBIGUOUS_INPUT = "ambiguous_input"
    NOT_FOUND = "not_found"
    NOT_AUTHORIZED = "not_authorized"
    STALE_INPUT = "stale_input"
    CONFLICT = "conflict"
    UPSTREAM_TIMEOUT = "upstream_timeout"
    UPSTREAM_ERROR = "upstream_error"
    RATE_LIMITED = "rate_limited"
    MALFORMED_MODEL_OUTPUT = "malformed_model_output"
    INJECTION_SUSPECTED = "injection_suspected"
    BUDGET_EXCEEDED = "budget_exceeded"
    INTERNAL = "internal"


class Recovery(StrEnum):
    RETRY = "retry"  # retried automatically within the capability policy
    ASK_HUMAN = "ask_human"  # surfaced to the cabinet as a question
    FALLBACK = "fallback"  # the capability's declared fallback runs
    REFUSE = "refuse"  # stop, log, never retry
    FAIL = "fail"  # stop and report


ERROR_BEHAVIOR: dict[ErrorCode, Recovery] = {
    ErrorCode.INVALID_INPUT: Recovery.ASK_HUMAN,
    ErrorCode.AMBIGUOUS_INPUT: Recovery.ASK_HUMAN,
    ErrorCode.NOT_FOUND: Recovery.FAIL,
    ErrorCode.NOT_AUTHORIZED: Recovery.REFUSE,
    ErrorCode.STALE_INPUT: Recovery.FAIL,
    ErrorCode.CONFLICT: Recovery.ASK_HUMAN,
    ErrorCode.UPSTREAM_TIMEOUT: Recovery.RETRY,
    ErrorCode.UPSTREAM_ERROR: Recovery.RETRY,
    ErrorCode.RATE_LIMITED: Recovery.RETRY,
    ErrorCode.MALFORMED_MODEL_OUTPUT: Recovery.RETRY,
    ErrorCode.INJECTION_SUSPECTED: Recovery.REFUSE,
    ErrorCode.BUDGET_EXCEEDED: Recovery.FALLBACK,
    ErrorCode.INTERNAL: Recovery.FAIL,
}


class Error(Contract):
    code: ErrorCode
    message: str = Field(max_length=1000)

    @property
    def recovery(self) -> Recovery:
        return ERROR_BEHAVIOR[self.code]


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Issue(Contract):
    """A finding about the data (e.g. a time not in 24-hour format). Not a failure of the call."""

    code: Annotated[str, StringConstraints(pattern=r"^[a-z_]+(\.[a-z0-9_]+)+$")]
    severity: Severity
    path: str | None = None
    message: str = Field(max_length=500)
    fix: str | None = Field(default=None, max_length=300)


class Question(Contract):
    """Something only a human can answer before the work can continue."""

    question_id: Slug
    text: str = Field(max_length=400)
    path: str | None = None
    choices: list[str] = Field(default_factory=list)
    blocking: bool = True


# ------------------------------------------------------------------------- trace


class TraceMeta(Contract):
    trace_id: Annotated[str, StringConstraints(min_length=8, max_length=64)]
    capability: Slug
    capability_version: Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
    prompt_version: str | None = None
    model: str | None = None
    started_at: datetime
    latency_ms: int = Field(ge=0)
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    cost_usd: Decimal = Field(default=Decimal("0"), ge=0)
    retries: int = Field(default=0, ge=0)
    replayed: bool = False


# ------------------------------------------------------------------------ result


class Status(StrEnum):
    OK = "ok"
    NEEDS_INPUT = "needs_input"
    FAILED = "failed"


T = TypeVar("T", bound=BaseModel)


class Result(Contract, Generic[T]):
    """The envelope every capability returns."""

    status: Status
    data: T | None = None
    issues: list[Issue] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    error: Error | None = None
    degraded: bool = Field(default=False, description="True when a declared fallback produced the data")
    trace: TraceMeta

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.status is Status.OK and (self.data is None or self.error is not None):
            raise ValueError("OK results carry data and no error")
        if self.status is Status.FAILED and (self.error is None or self.data is not None):
            raise ValueError("FAILED results carry an error and no data")
        if self.status is Status.NEEDS_INPUT and not any(q.blocking for q in self.questions):
            raise ValueError("NEEDS_INPUT results carry at least one blocking question")
        return self
