"""Backend objects -> the screen shapes in the UI spec (web/src/api/types.ts). Plain dicts, JSON-ready.

The capability contracts stay as they are; these are HTTP view models only. Where the backend has no
data yet (proposal answers before T-16, drafts before Joey's templates are wired), the field is empty,
never made up.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from clubops.api.store import PlannedEvent
from clubops.contracts.calendar import CalendarItem
from clubops.contracts.common import SourceKind, SourceRef
from clubops.contracts.event import Audience, EventRecord, EventSpec
from clubops.contracts.knowhow import (
    ItemStatus,
    Kind,
    KnowHowItem,
    KnowHowProposal,
    RelationshipDetails,
    RuleDetails,
    Scope,
)
from clubops.contracts.planning import TaskState
from clubops.contracts.rules import Applicability
from clubops.knowhow.store import AUTO_MEMBER

BEIRUT = ZoneInfo("Asia/Beirut")

_KIND = {
    SourceKind.DOCUMENT: "document",
    SourceKind.FORM: "document",
    SourceKind.EMAIL: "email",
    SourceKind.RETROSPECTIVE: "debrief",
}
_AUTHORITY = {
    SourceKind.DOCUMENT: "official_document",
    SourceKind.FORM: "official_document",
    SourceKind.EMAIL: "office_email",
    SourceKind.USER_INPUT: "stated_by_president",
}


def source(item: KnowHowItem, ref: SourceRef | None = None) -> dict[str, Any]:
    ref = ref or item.sources[0]
    out: dict[str, Any] = {
        "item_id": item.item_id,
        "label": ref.locator or ref.source_id,
        "kind": _KIND.get(ref.kind, "note"),
    }
    if ref.quote:
        out["quote"] = ref.quote
    if ref.kind in _AUTHORITY:
        out["authority"] = _AUTHORITY[ref.kind]
    return out


# ------------------------------------------------------------------- events


def _local(dt: datetime | None) -> datetime | None:
    return dt.astimezone(BEIRUT) if dt else None


def fields(spec: EventSpec) -> dict[str, str]:
    start, end = _local(spec.start), _local(spec.end)
    yes_no = {True: "yes", False: "no", None: ""}
    audience = {Audience.AUB_ONLY: "AUB students only", Audience.AUB_AND_GUESTS: "AUB and outside guests", None: ""}
    attendance = spec.expected_attendance
    return {
        "title": spec.title or "",
        "date": start.date().isoformat() if start else "",
        "time": start.strftime("%H:%M") if start else "",
        "end_time": end.strftime("%H:%M") if end else "",
        "venue": spec.venue.name if spec.venue else "",
        "audience": audience[spec.audience],
        "expected_attendance": f"{attendance.low}-{attendance.high}" if attendance else "",
        "budget": str(spec.estimated_budget.amount) if spec.estimated_budget else "",
        "sponsors": "",
        "has_prizes": yes_no[spec.has_prizes],
        "catering": yes_no[spec.has_catering],
        "partner_clubs": ", ".join(spec.collaborating_clubs),
        "description": spec.description or "",
    }


def _origins(spec: EventSpec) -> dict[str, dict[str, str]]:
    return {k: {"origin": "stated" if v else "missing"} for k, v in fields(spec).items()}


def tasks(
    event: PlannedEvent, changes: dict[str, tuple[str | None, str | None]], rules: dict[str, KnowHowItem], today: date
) -> list[dict[str, Any]]:
    if event.plan is None:
        return []
    by_req = {}
    if event.rules is not None:
        for d in event.rules.requirements:
            by_req[d.requirement.requirement_id] = d.from_items[0]
    out = []
    for t in event.plan.tasks:
        task_id = f"{event.spec.event_id}/{t.task_id}"
        state, owner = changes.get(task_id, (None, None))
        current = state or (
            TaskState.OVERDUE if t.due < today else TaskState.DUE_TODAY if t.due == today else TaskState.TODO
        )
        row: dict[str, Any] = {
            "task_id": task_id,
            "event_id": event.spec.event_id,
            "title": t.title,
            "due": t.due.isoformat(),
            "owner_role": owner or (t.owner_role.value if t.owner_role else "president"),
            "state": str(current),
        }
        if t.requirement_id:
            row["requirement_id"] = t.requirement_id
            item = rules.get(by_req.get(t.requirement_id, ""))
            if item is not None:
                row["source"] = source(item)
        out.append(row)
    return out


def approvals(event: PlannedEvent, rules: dict[str, KnowHowItem]) -> list[dict[str, Any]]:
    if event.rules is None:
        return []
    due = {t.task_id: t.due.isoformat() for t in (event.plan.tasks if event.plan else [])}
    reasons = {v.item_id: v.reason for v in event.rules.verdicts if v.verdict is not Applicability.NOT_APPLICABLE}
    out = []
    for d in event.rules.requirements:
        req, rule_id = d.requirement, d.from_items[0]
        item = rules.get(rule_id)
        out.append(
            {
                "approval_id": req.requirement_id,
                "name": req.name,
                "why": reasons.get(rule_id, ""),
                "deadline": due.get(req.requirement_id, ""),
                "status": "needed",
                "uncertain": d.uncertain,
                "source": source(item) if item else {"item_id": rule_id, "label": rule_id},
            }
        )
    return out


def summary(record: EventRecord | None, event: PlannedEvent, task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    spec = event.spec
    start, end = _local(spec.start), _local(spec.end)
    return {
        "event_id": spec.event_id,
        "title": spec.title or (record.title if record else "Untitled event"),
        "start": start.isoformat() if start else "",
        "end": end.isoformat() if end else "",
        "venue": spec.venue.name if spec.venue else "",
        "status": record.status.value if record else "draft",
        "task_count": len(task_rows),
        "tasks_done": sum(t["state"] == "done" for t in task_rows),
        "overdue_tasks": sum(t["state"] == "overdue" for t in task_rows),
        "event_type": spec.event_type.value if spec.event_type else "",
        "plan_outdated": event.plan_outdated,
    }


def detail(
    record: EventRecord | None, event: PlannedEvent, task_rows: list[dict[str, Any]], rules: dict[str, KnowHowItem]
) -> dict[str, Any]:
    out = summary(record, event, task_rows)
    out.update(
        {
            "revision": event.spec.revision,
            "fields": fields(event.spec),
            "origins": _origins(event.spec),
            "approvals": approvals(event, rules),
            "tasks": task_rows,
            "proposal": [],  # T-16
            "drafts": {},
            "tips": [],
            "leaders": [],
            "route": "",
        }
    )
    if event.approved_at:
        out["approved_at"], out["approved_by"] = event.approved_at, event.approved_by
    return out


# --------------------------------------------------------------- knowledge


def tab(item: KnowHowItem) -> str:
    if item.kind is Kind.RULE:
        return "rules"
    if isinstance(item.details, RelationshipDetails):
        return "sponsors" if item.details.party_type == "sponsor" else "contacts"
    return "tips"


def knowledge(item: KnowHowItem, history: list[KnowHowItem], today: date) -> dict[str, Any]:
    checked = item.last_confirmed_at or item.verified_at
    outdated = item.valid_to is not None and item.valid_to < today
    out: dict[str, Any] = {
        "item_id": item.item_id,
        "title": item.title,
        "statement": item.statement,
        "tab": tab(item),
        "kind": item.kind.value,
        "scope": item.scope.value,
        "sources": [source(item, s) for s in item.sources],
        "last_checked": checked.date().isoformat() if checked else "",
        "valid_to": item.valid_to.isoformat() if item.valid_to else None,  # null: no end date (F-305)
        "status": "retired" if item.status is ItemStatus.RETIRED else "may_be_outdated" if outdated else "current",
        "history": [
            {
                "date": (v.verified_at or v.sources[0].observed_at).date().isoformat(),
                "description": f"version {v.version}: {v.status.value}",
                "actor": "ClubOps (automatic)" if v.verified_by == AUTO_MEMBER else v.verified_by or "",
            }
            for v in history
        ],
        "used_in": [],
        "auto": bool(history)
        and history[0].verified_by == AUTO_MEMBER,  # first added by code from trusted OSA mail (D-138)
    }
    if isinstance(item.details, RuleDetails):
        out["triggers"] = ", ".join(item.details.triggers)
        out["requirements"] = "; ".join(r.name for r in item.details.requirements)
        leads = [r.lead_time_days for r in item.details.requirements if r.lead_time_days is not None]
        if leads:
            out["lead_time_days"] = max(leads)
    if isinstance(item.details, RelationshipDetails) and item.details.offers:
        out["offers"] = ", ".join(item.details.offers)
    return out


def review_card(p: KnowHowProposal, target: KnowHowItem | None = None) -> dict[str, Any]:
    """A proposed fact for the Review screen. ``target`` is the existing fact it merges with, updates or disputes."""
    c = p.candidate
    kind = (
        "disagreement"
        if p.conflicts_with
        else "merge"
        if p.op.value in ("merge", "update")
        else ("rule" if c.kind is Kind.RULE else "fact")
    )
    card: dict[str, Any] = {
        "id": p.proposal_id,
        "type": kind,
        "title": c.title,
        "statement": c.statement,
        "source": source(c),
        "group": tab(c),
        "kind": c.kind.value,
        "status": "pending",
        "op": p.op.value,
        "shared": c.scope is Scope.AUB,  # true: every AUB club will see it once approved (D-91)
        "valid_to": c.valid_to.isoformat() if c.valid_to else None,  # null: no end date, it never expires (F-305)
        "why": p.rationale[:300],  # why ClubOps proposed this action, plain text (F-311)
    }
    if isinstance(c.details, RuleDetails):
        leads = [r.lead_time_days for r in c.details.requirements if r.lead_time_days is not None]
        if leads:
            card["lead_time_days"] = max(leads)  # the notice period a person may correct before approving (F-309)
    if target is not None:
        if p.op.value in ("merge", "update"):
            # A new version stays in the known fact's layer (F-163), so the box cannot change it (F-310).
            card["shared"] = target.scope is Scope.AUB
            card["shared_locked"] = True
        card["alternative"] = {
            "statement": target.statement,
            "source": source(target),
            "valid_to": target.valid_to.isoformat() if target.valid_to else None,
        }
    if p.injection_flags:
        card["warning"] = "This source contained instructions; they were ignored. Check the fact carefully."
    if "may be outdated" in p.rationale:
        card["outdated"] = True
    if "sender is not on the OSA list" in p.rationale:
        card["unlisted"] = True  # a person chose to read an e-mail whose sender is not on the OSA list (D-136)
    return card


# ---------------------------------------------------------------- calendar


def calendar_item(item: CalendarItem) -> dict[str, Any]:
    out = item.model_dump(mode="json")
    if item.event_id and item.kind.value == "task":
        out["task_id"] = item.item_id
    return out
