"""A plain-code rule check the agent can use until T-15 adds the model-judged version.

Each rule lists triggers (event facts such as 'non_aub_guests' or 'prizes'). A rule:
- applies when one of its triggers is true for the event,
- is uncertain when a trigger depends on a fact we don't know yet, or is a trigger this
  code doesn't recognise (never silently skipped, D-49),
- does not apply only when every trigger is known to be false.
"""

from __future__ import annotations

from collections.abc import Callable

from clubops.capabilities.plan import derive_requirements
from clubops.contracts.event import Admission, Audience, EventSpec, Funding, VenueKind
from clubops.contracts.knowhow import KnowHowItem, RuleDetails
from clubops.contracts.rules import Applicability, RuleApplication, RuleVerdict

# trigger -> (field it reads, test). The test returns None when the fact is not known yet.
_Test = Callable[[EventSpec], bool | None]


def _venue_is(kind: VenueKind) -> _Test:
    return lambda s: None if s.venue is None else s.venue.kind is kind


def _funding_has(source: Funding) -> _Test:
    return lambda s: None if not s.funding else source in s.funding


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
    "speaker": ("spec.speakers", lambda s: bool(s.speakers)),
    "off_campus": ("spec.venue", _venue_is(VenueKind.OFF_CAMPUS)),
    "green_field": ("spec.venue", _venue_is(VenueKind.GREEN_FIELD)),
    "materials": ("spec.needs_materials", lambda s: s.needs_materials),
}


def _norm(trigger: str) -> str:
    return trigger.strip().lower().replace("-", "_").replace(" ", "_")


def judge(spec: EventSpec, rule: KnowHowItem) -> RuleVerdict:
    if not isinstance(rule.details, RuleDetails):
        raise TypeError(f"{rule.item_id} is not a rule")
    true_facts: list[str] = []
    false_facts: list[str] = []
    unknown: list[str] = []
    for raw in rule.details.triggers:
        known = TRIGGERS.get(_norm(raw))
        if known is None:
            unknown.append(f"'{raw}' needs a person to judge")
            continue
        path, test = known
        value = test(spec)
        if value is True:
            true_facts.append(path)
        elif value is False:
            false_facts.append(path)
        else:
            unknown.append(f"{path.removeprefix('spec.')} not known yet")
    if true_facts:
        verdict, reason, used = Applicability.APPLIES, "the event has: " + ", ".join(true_facts), true_facts
    elif unknown:
        verdict, reason, used = Applicability.UNCERTAIN, "; ".join(unknown), false_facts
    else:
        verdict, reason, used = Applicability.NOT_APPLICABLE, "none of its triggers fit the event", false_facts
    return RuleVerdict(
        item_id=rule.item_id,
        item_version=rule.version,
        verdict=verdict,
        reason=reason[:400],
        facts_used=sorted(set(used)),
    )


def check_rules(spec: EventSpec, rules: list[KnowHowItem]) -> RuleApplication:
    """Judge every current rule. Same input, same output."""
    rulebook = [r for r in rules if isinstance(r.details, RuleDetails)]
    verdicts = [judge(spec, r) for r in rulebook]
    return RuleApplication(
        event_id=spec.event_id,
        spec_revision=spec.revision,
        rulebook=[(r.item_id, r.version) for r in rulebook],
        verdicts=verdicts,
        requirements=derive_requirements(verdicts, {r.item_id: r for r in rulebook}),
    )
