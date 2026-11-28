"""The plain-code part of the rule check (T-15). Facts the code can read are judged here, for free;
what only the event description can tell (publicity, risk, filming...) is left to the model judge
(`agent/rules_judge.py`), and stays 'not sure' when the model can't tell either.

Each rule lists triggers (event facts such as 'non_aub_guests' or 'prizes'). A rule:
- applies when one of its triggers is true for the event,
- is uncertain when a trigger depends on a fact we don't know yet, or is a trigger this
  code doesn't recognise (never silently skipped, D-49),
- does not apply only when every trigger is known to be false.
"""

from __future__ import annotations

from collections.abc import Callable

from clubops.capabilities.plan import derive_requirements
from clubops.contracts.event import Admission, Audience, EventSpec, EventType, Funding, VenueKind
from clubops.contracts.knowhow import KnowHowItem, RuleDetails
from clubops.contracts.rules import Applicability, RuleApplication, RuleVerdict

# trigger -> (field it reads, test). The test returns None when the fact is not known yet.
_Test = Callable[[EventSpec], bool | None]


def _venue_is(kind: VenueKind) -> _Test:
    return lambda s: None if s.venue is None else s.venue.kind is kind


def _funding_has(source: Funding) -> _Test:
    return lambda s: None if not s.funding else source in s.funding


def _budget_over(limit: int) -> _Test:
    def test(s: EventSpec) -> bool | None:
        if s.estimated_budget is None:
            return False if s.funding == [Funding.NO_EXPENSES] else None
        return s.estimated_budget.currency == "USD" and s.estimated_budget.amount > limit

    return test


def _expenses(s: EventSpec) -> bool | None:
    if s.funding == [Funding.NO_EXPENSES]:
        return False
    if Funding.CLUB_ACCOUNT in s.funding or (s.estimated_budget is not None and s.estimated_budget.amount > 0):
        return True
    return None


def _major(s: EventSpec) -> bool | None:
    if s.event_type in (EventType.CONFERENCE, EventType.GALA_DINNER):
        return True
    over = _budget_over(1000)(s)
    if over:
        return True
    return False if over is False and s.event_type is not None else None


_HOSTLER_WORDS = ("hostler", "chsc", "track", "pool", "court", "green field")


def _hostler(s: EventSpec) -> bool | None:
    if s.venue is None:
        return None
    return s.venue.kind is VenueKind.GREEN_FIELD or any(w in s.venue.name.lower() for w in _HOSTLER_WORDS)


def _indoor_room(s: EventSpec) -> bool | None:
    if s.venue is None:
        return None
    if s.venue.kind in (VenueKind.WEST_HALL, VenueKind.CLASSROOM):
        return True
    return None if s.venue.kind is VenueKind.OTHER_ON_CAMPUS else False


# Triggers only the event description can settle; the model judge decides them.
MODEL_TRIGGERS = frozenset({"publicity", "external_org", "risky_activity", "filming", "fundraiser"})

TRIGGERS: dict[str, tuple[str, _Test]] = {
    "always": ("spec", lambda s: True),
    "non_aub_guests": (
        "spec.audience",
        lambda s: None if s.audience is None else s.audience is Audience.AUB_AND_GUESTS,
    ),
    "prizes": ("spec.has_prizes", lambda s: s.has_prizes),
    "catering": ("spec.has_catering", lambda s: s.has_catering),
    "food": ("spec.has_catering", lambda s: s.has_catering),
    "sales": ("spec.has_sales", lambda s: s.has_sales),
    "tickets": ("spec.admission", lambda s: None if s.admission is None else s.admission is Admission.TICKET),
    "external_sponsor": ("spec.funding", _funding_has(Funding.EXTERNAL_SPONSOR)),
    "club_account": ("spec.funding", _funding_has(Funding.CLUB_ACCOUNT)),
    "speaker": ("spec.speakers", lambda s: True if s.speakers else None),
    "partner_club": ("spec.collaborating_clubs", lambda s: True if s.collaborating_clubs else None),
    "usfc": ("spec.funding", _funding_has(Funding.USFC)),
    "expenses": ("spec.funding", _expenses),
    "budget_over_200": ("spec.estimated_budget", _budget_over(200)),
    "major_event": ("spec.event_type", _major),
    "hostler_venue": ("spec.venue", _hostler),
    "indoor_room": ("spec.venue", _indoor_room),
    "off_campus": ("spec.venue", _venue_is(VenueKind.OFF_CAMPUS)),
    "green_field": ("spec.venue", _venue_is(VenueKind.GREEN_FIELD)),
    "materials": ("spec.needs_materials", lambda s: s.needs_materials),
}


def _norm(trigger: str) -> str:
    return trigger.strip().lower().replace("-", "_").replace(" ", "_")


def _plain(path: str) -> str:
    """'spec.has_prizes' -> 'prizes'; a bare 'spec' is the rule that fits every event."""
    name = path.removeprefix("spec").removeprefix(".").removeprefix("has_")
    return name.replace("_", " ") or "every event"


def judge(spec: EventSpec, rule: KnowHowItem) -> RuleVerdict:
    if not isinstance(rule.details, RuleDetails):
        raise TypeError(f"{rule.item_id} is not a rule")
    true_facts: list[str] = []
    false_facts: list[str] = []
    unknown: list[str] = []
    club_only: list[str] = []
    for raw in rule.details.triggers:
        known = TRIGGERS.get(_norm(raw))
        if known is None:
            if _norm(raw) in MODEL_TRIGGERS:
                unknown.append(f"'{raw}' depends on the event description")
            elif "event" in raw.lower():  # may concern this event (a deadline, a cut-off): keep it visible
                unknown.append(f"'{raw}' may concern this event; check it")
            elif " " in raw.strip():  # a free-text phrase about running the club, not about one event (F-339)
                club_only.append(raw)
            else:  # a key the code does not know yet: never silently skipped (D-49)
                unknown.append(f"'{raw}' needs a person to judge")
            continue
        path, test = known
        value = test(spec)
        if value is True:
            true_facts.append(path)
        elif value is False:
            false_facts.append(path)
        else:
            unknown.append(f"{path.removeprefix('spec.')} not known yet")  # planner reads this exact wording
    if true_facts:
        verdict, reason, used = (
            Applicability.APPLIES,
            "applies because of: " + ", ".join(_plain(f) for f in true_facts),
            true_facts,
        )
    elif unknown:
        verdict, reason, used = Applicability.UNCERTAIN, "; ".join(unknown), false_facts
    elif club_only and not false_facts:
        verdict, reason, used = Applicability.NOT_APPLICABLE, "about running the club, not about this event", ["spec"]
    else:
        verdict, reason, used = Applicability.NOT_APPLICABLE, "none of its triggers fit the event", false_facts
    return RuleVerdict(
        item_id=rule.item_id,
        item_version=rule.version,
        verdict=verdict,
        reason=reason[:400],
        facts_used=sorted(set(used)),
    )


def check_rules(spec: EventSpec, rules: list[KnowHowItem], budget: object = None) -> RuleApplication:
    """Judge every current rule from the event facts. Same input, same output; never costs money
    (``budget`` is accepted so it can stand in for the model judge)."""
    rulebook = [r for r in rules if isinstance(r.details, RuleDetails)]
    verdicts = [judge(spec, r) for r in rulebook]
    return RuleApplication(
        event_id=spec.event_id,
        spec_revision=spec.revision,
        rulebook=[(r.item_id, r.version) for r in rulebook],
        verdicts=verdicts,
        requirements=derive_requirements(verdicts, {r.item_id: r for r in rulebook}),
    )
