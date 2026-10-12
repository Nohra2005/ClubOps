"""The single source of truth for what each capability takes, returns, and is allowed to do.

docs/contracts.md is generated from this table (scripts/export_schemas.py), and tests check
that every capability's request and response types are real contract models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel

from clubops.contracts import approvals, event, forms, handover, knowhow, planning, rules, sponsors


class Control(StrEnum):
    AGENTIC = "agentic"  # a model decides
    DETERMINISTIC = "deterministic"  # plain code, same input -> same output
    HUMAN = "human"  # only a verified cabinet member can do it


class Stability(StrEnum):
    FROZEN = "frozen"  # changing it needs a contract-change PR (CONTRIBUTING.md)
    PROVISIONAL = "provisional"  # may change until its phase starts


@dataclass(frozen=True)
class Policy:
    timeout_s: float
    max_retries: int
    fallback: str | None = None


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    version: str
    control: Control
    stability: Stability
    request: type[BaseModel]
    response: type[BaseModel]
    policy: Policy
    summary: str
    may_read: tuple[str, ...] = field(default_factory=tuple)
    may_propose: tuple[approvals.ActionKind, ...] = field(default_factory=tuple)
    requires_cabinet: bool = False
    takes_untrusted: bool = False


DETERMINISTIC = Policy(timeout_s=2.0, max_retries=0)

CAPABILITIES: tuple[CapabilitySpec, ...] = (
    # ------------------------------------------------------------- know-how
    CapabilitySpec(
        name="capture",
        version="0.1.0",
        control=Control.AGENTIC,
        stability=Stability.FROZEN,
        request=knowhow.CaptureRequest,
        response=knowhow.CaptureResult,
        policy=Policy(timeout_s=60, max_retries=2, fallback="return no proposals; sources stay queued"),
        summary="Extract know-how proposals (create, merge, update, retire, contradiction) from untrusted sources.",
        may_read=("knowhow.verified",),
        takes_untrusted=True,
    ),
    CapabilitySpec(
        name="verify",
        version="0.1.0",
        control=Control.HUMAN,
        stability=Stability.FROZEN,
        request=knowhow.VerifyRequest,
        response=knowhow.VerifyResult,
        policy=DETERMINISTIC,
        summary="A cabinet member accepts, edits or rejects a proposal. The only way into the knowledge base.",
        requires_cabinet=True,
    ),
    CapabilitySpec(
        name="surface",
        version="0.1.0",
        control=Control.AGENTIC,
        stability=Stability.FROZEN,
        request=knowhow.SurfaceRequest,
        response=knowhow.SurfaceResult,
        policy=Policy(timeout_s=20, max_retries=1, fallback="tag-match over verified items, no ranking"),
        summary="Rank the verified know-how relevant to what the cabinet is about to do.",
        may_read=("knowhow.verified",),
    ),
    CapabilitySpec(
        name="ask",
        version="0.1.0",
        control=Control.AGENTIC,
        stability=Stability.FROZEN,
        request=knowhow.AskRequest,
        response=knowhow.Answer,
        policy=Policy(timeout_s=20, max_retries=1, fallback="answer 'not known'"),
        summary="Answer a question from verified know-how only, with citations, or say it is not known.",
        may_read=("knowhow.verified",),
    ),
    CapabilitySpec(
        name="find-gaps",
        version="0.1.0",
        control=Control.AGENTIC,
        stability=Stability.FROZEN,
        request=knowhow.GapRequest,
        response=knowhow.GapReport,
        policy=Policy(timeout_s=30, max_retries=1, fallback="deterministic checks only: stale, unverified, unowned"),
        summary="Find missing, stale, unverified or contradictory know-how and phrase questions about it.",
        may_read=("knowhow.all",),
    ),
    # ------------------------------------------------------------- handover
    CapabilitySpec(
        name="build-handover",
        version="0.1.0",
        control=Control.DETERMINISTIC,
        stability=Stability.FROZEN,
        request=handover.HandoverRequest,
        response=handover.HandoverPack,
        policy=DETERMINISTIC,
        summary="Assemble a role's handover pack from verified know-how and open gaps; every line cites its source.",
        may_read=("knowhow.verified", "knowhow.gaps"),
        may_propose=(approvals.ActionKind.SIGN_OFF_HANDOVER, approvals.ActionKind.TRANSFER_ROLE),
    ),
    CapabilitySpec(
        name="plan-interview",
        version="0.1.0",
        control=Control.AGENTIC,
        stability=Stability.FROZEN,
        request=handover.InterviewRequest,
        response=handover.Interview,
        policy=Policy(timeout_s=30, max_retries=1, fallback="ask each gap's question verbatim, highest priority first"),
        summary="Turn a role's gaps into a short, prioritized interview for the outgoing officer.",
        may_read=("knowhow.all",),
    ),
    # --------------------------------------------------------- event packet
    CapabilitySpec(
        name="intake",
        version="0.1.0",
        control=Control.AGENTIC,
        stability=Stability.FROZEN,
        request=event.IntakeRequest,
        response=event.EventDraft,
        policy=Policy(timeout_s=30, max_retries=2, fallback="ask the cabinet to fill the missing fields"),
        summary="Turn a free-text event description into an EventSpec with per-field provenance.",
        may_read=("knowhow.verified", "club.profile"),
        takes_untrusted=True,
    ),
    CapabilitySpec(
        name="apply-rules",
        version="0.1.0",
        control=Control.AGENTIC,
        stability=Stability.FROZEN,
        request=rules.RuleApplicationRequest,
        response=rules.RuleApplication,
        policy=Policy(
            timeout_s=45, max_retries=2, fallback="mark every rule 'uncertain' so nothing is silently skipped"
        ),
        summary="Judge each current AUB rule as applies / not applicable / uncertain; code derives requirements.",
        may_read=("knowhow.verified:rule",),
    ),
    CapabilitySpec(
        name="draft-proposal",
        version="0.1.0",
        control=Control.AGENTIC,
        stability=Stability.FROZEN,
        request=forms.DraftProposalRequest,
        response=forms.ProposalDraft,
        policy=Policy(
            timeout_s=45, max_retries=2, fallback="fill mapped fields only; free-text fields left for a human"
        ),
        summary="Answer the OSA proposal form from the spec, club profile and rules, each answer with its origin.",
        may_read=("knowhow.verified", "club.profile", "forms"),
        may_propose=(approvals.ActionKind.SUBMIT_PROPOSAL,),
    ),
    CapabilitySpec(
        name="plan-backward",
        version="0.1.0",
        control=Control.DETERMINISTIC,
        stability=Stability.FROZEN,
        request=planning.PlanRequest,
        response=planning.Plan,
        policy=DETERMINISTIC,
        summary="Compute task due dates backward from the event date using rule lead times.",
        may_propose=(approvals.ActionKind.SEND_CALENDAR_INVITE,),
    ),
    # ------------------------------------------------------------ sponsors
    CapabilitySpec(
        name="suggest-replacement",
        version="0.0.1",
        control=Control.AGENTIC,
        stability=Stability.PROVISIONAL,
        request=sponsors.ReplacementRequest,
        response=sponsors.ReplacementSuggestions,
        policy=Policy(timeout_s=20, max_retries=1, fallback="list verified sponsors offering the same category"),
        summary="When a sponsor drops out, propose replacements for the same category from the club's relationships.",
        may_read=("knowhow.verified:relationship",),
        may_propose=(approvals.ActionKind.SEND_EMAIL,),
    ),
)


def get(name: str) -> CapabilitySpec:
    for spec in CAPABILITIES:
        if spec.name == name:
            return spec
    raise KeyError(name)
