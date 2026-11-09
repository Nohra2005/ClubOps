"""Planning evaluation (T-06, T-26): which approvals does each system say a past event needed?

Four systems get the same event description (built from the frozen test row, never its notes or answers):
1. checklist  - plain code: keywords in the description tick boxes on the OSA checklist; no model.
2. plain      - one model call: the approval codes and what each means, but not when each is needed.
3. rulebook   - one model call with the 25 AUB rules pasted in.
4. clubops    - the planning agent with the rulebook and the club's memory, as in the app. A simulated user
                answers its questions (see below). Memory holds only facts learned from events *before* the
                one being planned (no leakage, eval/FROZEN.md).

Two settings:
- full start (default): every system gets the whole description; the simulated user repeats it.
- short start (``short_start=True``): every system gets only what a president types first (the event and
  its date). The agent may ask; the simulated user answers each question only from the matching fields of
  that event's row (place, people, guests, sponsors, money, partners), or "I don't know". It never uses the
  notes or the labels, and never says more than the row. One-call systems cannot ask, which is the point:
  it measures what asking adds.

Scoring compares the predicted codes with the president's labels (`approvals_real`), on the codes she labels
(SCORED). Codes outside that set (e.g. LOGO, RCPT) are ignored for every system alike.
"""

from __future__ import annotations

import csv
import re
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import Field

from clubops import debuglog
from clubops.agent.planner import Planner, RunState
from clubops.contracts.agent import PlanEventRequest
from clubops.contracts.common import Contract, SourceKind, SourceRef, Untrusted
from clubops.contracts.knowhow import ItemStatus, KnowHowItem
from clubops.knowhow.directory import Directory
from clubops.knowhow.store import KnowHowStore
from clubops.model.budget import Budget
from clubops.model.client import ModelClient, ModelRequest

# The approval codes the president labels (approval-codes.md without OFF, LOGO and RCPT).
SCORED: dict[str, str] = {
    "PROP": "OSA event proposal",
    "ADV": "adviser approves the proposal",
    "EXP": "expense form",
    "SPON": "sponsorship document",
    "NOBAN": "check the sponsor is not a banned category",
    "PRIZE": "prize paperwork (winners e-mailed)",
    "POST": "OSA approval and stamp for posters and posts",
    "HOST": "Hostler / CHSC facility booking",
    "GUEST": "approval and name list for non-AUB guests",
    "TICK": "list of participants and payments",
    "COLLAB": "expense/revenue split with partner clubs",
    "EXT": "overview of an external organization",
    "SPEAK": "speaker details and CV",
    "SAFE": "safety (EHSRM) recommendation",
    "FILM": "filming authorization",
    "WAIVER": "liability waiver",
    "VOTE": "members' vote for spending over $200",
    "MAJOR": "6 weeks lead time for major events",
    "SEC": "security / roads / Red Cross coordination",
    "FOOD": "food items and suppliers",
    "ROOM": "room booking",
    "FUND": "proof of payment to the beneficiary",
    "IMPACT": "impact report after the event",
}
_CODE = re.compile(r"\b(no\s+)?([A-Z]{3,6})\b")


@dataclass(frozen=True)
class Case:
    case_id: str
    on: date
    description: str
    truth: frozenset[str]
    # The row's event fields (never notes or labels), for the simulated user's answers in short start.
    details: tuple[tuple[str, str], ...] = ()
    short_start: bool = False


def truth_codes(label: str) -> frozenset[str]:
    """Codes in the president's label, minus those written as 'no X'."""
    return frozenset(m.group(2) for m in _CODE.finditer(label) if m.group(2) in SCORED and not m.group(1))


_DAY = re.compile(r"(\d{4})-(\d{2})(?:-(\d{2}))?")
PLANNING_LEAD = timedelta(days=30)  # the club starts planning about a month before (deadlines are then reachable)
UNKNOWN_DATE = date(2026, 3, 16)  # mid-semester stand-in when a past event's date was never recorded


def event_date(text: str) -> date:
    """First date in the cell: '2026-10-07', '2025-11-06 to 2025-11-07' -> that day; '2025-12 (day not given)'
    -> the 15th; 'not given' -> UNKNOWN_DATE. Only used as the planner's 'today' and for the no-leakage filter."""
    m = _DAY.search(text or "")
    if not m:
        return UNKNOWN_DATE
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 15))


def describe(row: dict[str, str]) -> str:
    """The event as a cabinet member would type it. Never uses the notes or the labels."""
    when = row["date"] if _DAY.search(row["date"] or "") else "a date not given"
    parts = [
        f"{row['event']} on {when}",
        f"Place: {row['place']}",
        f"People: {row['people']}",
        f"Outside guests: {row['outside_guests']}",
        f"Sponsors or prizes: {row['sponsors_prizes']}",
        f"Money: {row['money']}",
        f"Partners: {row['partners']}",
    ]
    return ". ".join(p for p in parts if p and not p.endswith(": ")) + "."


DETAIL_FIELDS = {
    "place": "Place",
    "people": "People",
    "outside_guests": "Outside guests",
    "sponsors_prizes": "Sponsors or prizes",
    "money": "Money",
    "partners": "Partners",
}
# Which row field answers a question, by its words. Food has no column, so food questions get "I don't know".
_ASKS: list[tuple[str, str]] = [
    ("place", r"venue|where|place|location|room|field|hall|indoor|outdoor"),
    ("people", r"how many|number of|participants|attend|size|expect"),
    ("outside_guests", r"guest|outside|non-aub|external|public|open to|who can|audience|families"),
    ("sponsors_prizes", r"sponsor|prize|award|gift|giveaway"),
    ("money", r"money|cost|budget|fee|ticket|pay|price|fund|sell|sale|charge|spend|donat"),
    ("partners", r"partner|collab|other club|societ|co-host|together with"),
]


def opening(row: dict[str, str]) -> str:
    """What a president types first: the event and its date."""
    when = row["date"] if _DAY.search(row["date"] or "") else "a date not given"
    return f"{row['event']} on {when}."


def simulated_answer(case: Case, question: str) -> str:
    """The simulated president's reply: only the row fields the question is about, or "I don't know"."""
    if not case.short_start:
        return f"That's all I know: {case.description}"
    known = dict(case.details)
    q = question.lower()
    parts = [
        f"{DETAIL_FIELDS[name]}: {known[name]}"
        for name, words in _ASKS
        if re.search(words, q) and known.get(name, "").strip()
    ]
    return ". ".join(parts) + "." if parts else "I don't know."


def load_cases(path: Path, label_column: str = "approvals_real (you fill)", *, short_start: bool = False) -> list[Case]:
    cases = []
    for row in csv.DictReader(path.open(encoding="utf-8")):
        label = row.get(label_column, "") or ""
        if not label.strip() or label.strip().upper().startswith("DROP"):
            continue
        details = tuple((k, (row.get(k) or "").strip()) for k in DETAIL_FIELDS)
        text = opening(row) if short_start else describe(row)
        cases.append(Case(row["id"], event_date(row["date"]), text, truth_codes(label), details, short_start))
    return cases


# --------------------------------------------------------------------- systems

Predict = Callable[[Case], "Prediction"]


@dataclass
class Prediction:
    codes: frozenset[str]
    uncertain: frozenset[str] = frozenset()
    cost_usd: Decimal = Decimal("0")
    calls: int = 0
    error: str | None = None
    model_ms: int = 0  # time in model calls and in tools, from the agent's steps (ClubOps only)
    tool_ms: int = 0


_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (r"sponsor", ("SPON", "NOBAN")),
    (r"prize", ("PRIZE",)),
    (r"poster|flyer|instagram|post\b", ("POST",)),
    (r"green field|hostler|chsc|track|pool|court", ("HOST",)),
    (r"outside guest|non-aub|families|public|faculty|yes", ("GUEST",)),
    (r"ticket|fee|registration|\$\s?\d", ("TICK",)),
    (r"societ|clubs?\b", ("COLLAB",)),
    (r"ngo|external|company|office of|foundation", ("EXT",)),
    (r"speaker|talk|panel|lecture", ("SPEAK",)),
    (r"swim|beach|road|race|triathlon", ("SAFE",)),
    (r"film|video|drone|screening", ("FILM",)),
    (r"food|snack|coffee|catering|drinks|cookie", ("FOOD",)),
    (r"room|hall|auditorium", ("ROOM",)),
    (r"fundrais|donation|charity|for a cause", ("FUND",)),
    (r"\$|budget|buy|print|sticker", ("EXP",)),
]


def checklist(case: Case) -> Prediction:
    """Baseline 1: a plain OSA checklist ticked by keywords. No model, no cost."""
    text = case.description.lower()
    codes = {"PROP", "ADV", "IMPACT"}
    for pattern, ticks in _KEYWORDS:
        if re.search(pattern, text):
            codes.update(ticks)
    return Prediction(frozenset(codes))


class CodesAnswer(Contract):
    codes: list[str] = Field(max_length=30)
    reasons: str = Field(default="", max_length=1500)


PLAIN_VERSION = "eval-plain-v1"
RULEBOOK_VERSION = "eval-rulebook-v1"

_ASK = (
    "You help an AUB (American University of Beirut) student club. For the event below, list which of these "
    'approvals and documents the club needs. Answer JSON only: {"codes": [...], "reasons": "..."}.\n'
    "Codes:\n" + "\n".join(f"- {c}: {m}" for c, m in SCORED.items())
)


def model_baseline(client: ModelClient, rulebook_text: str | None, run: int = 1) -> Predict:
    """Baselines 2 and 3: one model call, without or with the AUB rules pasted in.

    Same settings as the app (temperature 0); each run has its own recordings, so repeated runs show how much
    the provider's answers vary."""

    def predict(case: Case) -> Prediction:
        system = _ASK + (f"\n\nAUB rules:\n{rulebook_text}" if rulebook_text else "")
        version = (RULEBOOK_VERSION if rulebook_text else PLAIN_VERSION) + (f"#r{run}" if run > 1 else "")
        budget = Budget(max_usd=Decimal("0.05"), max_steps=1)
        try:
            answer, usage = client.complete(
                ModelRequest(version, system, f"<event>\n{case.description}\n</event>", max_tokens=1200),
                CodesAnswer,
                budget,
            )
        except Exception as err:
            return Prediction(frozenset(), error=type(err).__name__, cost_usd=budget.spent_usd, calls=budget.steps)
        codes = frozenset(c.strip().upper() for c in answer.codes) & frozenset(SCORED)
        return Prediction(codes, cost_usd=usage.cost_usd, calls=1)

    return predict


def rulebook_text(rules: list[KnowHowItem]) -> str:
    return "\n".join(f"- [{r.tags[-1].upper()}] {r.title}: {r.statement}" for r in rules)


@dataclass
class ClubOpsSystem:
    """Baseline 4: the planning agent as in the app, with memory limited to earlier events."""

    make_planner: Callable[[KnowHowStore, Directory, Budget | None], Planner]
    store_for: Callable[[Case], KnowHowStore]
    directory_for: Callable[[Case], Directory]
    rule_codes: dict[str, str] = field(default_factory=dict)  # rule item id -> approval code

    def __call__(self, case: Case) -> Prediction:
        store, directory = self.store_for(case), self.directory_for(case)
        planner = self.make_planner(store, directory, None)
        words = Untrusted(
            content=case.description,
            source=SourceRef(
                kind=SourceKind.USER_INPUT, source_id=f"eval/{case.case_id}", observed_at=datetime.now(UTC)
            ),
        )
        try:
            state = planner.start(
                PlanEventRequest(club_id="eval-club", description=words, today=case.on - PLANNING_LEAD),
                f"run-{case.case_id.lower()}",
            )
            answers, continued = 0, False
            while True:  # the simulated user answers a few questions and clicks "continue" once, as in the app
                status = state.run.status.value
                if status == "waiting_for_user" and answers < (5 if case.short_start else 3):
                    answers += 1
                    state = planner.answer(state, simulated_answer(case, state.run.steps[-1].text))
                elif status == "at_limit" and case.short_start and not continued:
                    continued = True
                    state = planner.keep_going(state)
                else:
                    break
        except Exception as err:
            debuglog.log(
                "case",
                case=case.case_id,
                status="exception",
                error=repr(err)[:300],
                trace=traceback.format_exc()[-1500:],
            )
            return Prediction(frozenset(), error=type(err).__name__)
        finally:
            store.close()
            directory.close()
        debuglog.log(
            "case",
            case=case.case_id,
            status=str(state.run.status),
            steps=[
                f"{s.n} {s.tool} [{s.state}] model={s.model_ms}ms tool={s.tool_ms}ms: {s.text}" for s in state.run.steps
            ],
        )
        return self._codes(state)

    def _codes(self, state: RunState) -> Prediction:
        sure: set[str] = set()
        unsure: set[str] = set()
        if state.rules is not None:
            for d in state.rules.requirements:
                for item_id in d.from_items:
                    code = self.rule_codes.get(item_id)
                    if code in SCORED:
                        (unsure if d.uncertain else sure).add(code)
        return Prediction(
            frozenset(sure),
            frozenset(unsure - sure),
            cost_usd=state.run.cost_usd,
            calls=state.run.steps_used,
            error=None if state.run.status.value == "done" else state.run.status.value,
            model_ms=sum(st.model_ms or 0 for st in state.run.steps),
            tool_ms=sum(st.tool_ms or 0 for st in state.run.steps),
        )


def codes_by_rule(rules: list[KnowHowItem]) -> dict[str, str]:
    """The rulebook tags each rule with its approval code (last tag, e.g. 'prop')."""
    return {r.item_id: r.tags[-1].upper() for r in rules if r.tags}


def facts_before(path: Path, cases: list[Case], before: date, club_id: str) -> list[KnowHowItem]:
    """The president's facts learned from events before ``before`` (or from no event), as approved know-how."""
    when = {c.case_id: c.on for c in cases}
    out = []
    for row in csv.DictReader(path.open(encoding="utf-8")):
        source_event = (row.get("learned_from_event") or "").strip()
        learned_on = when.get(source_event)
        if source_event and (learned_on is None or learned_on >= before):
            continue
        scope_aub = (row.get("scope") or "").startswith("aub")
        out.append(
            KnowHowItem.model_validate(
                {
                    "item_id": f"kh-fact-{row['fact_id'].lower()}",
                    "scope": "club",  # stated by one president: kept club-level, never as an AUB rule
                    "club_id": club_id,
                    "title": row["statement"][:80],
                    "statement": row["statement"],
                    "details": {
                        "kind": "decision",
                        "decision": row["statement"][:300],
                        "rationale": "stated by the club president" + (" (AUB-wide practice)" if scope_aub else ""),
                    },
                    "sources": [
                        {
                            "kind": "user_input",
                            "source_id": f"facts/{row['fact_id']}",
                            "quote": row["statement"][:500],
                            "observed_at": datetime(2026, 10, 22, tzinfo=UTC),
                        }
                    ],
                    "support": {"events": [], "source_count": 1},
                    "status": ItemStatus.VERIFIED,
                    "verified_by": "m-tatiana-nohra",
                    "verified_at": datetime(2026, 10, 22, tzinfo=UTC),
                    "version": 1,
                }
            )
        )
    return out


# --------------------------------------------------------------------- scoring


@dataclass
class Score:
    caught: int = 0
    missed: int = 0
    false_alarms: int = 0
    unsure_caught: int = 0
    cost_usd: Decimal = Decimal("0")
    calls: int = 0
    errors: int = 0
    seconds: float = 0.0
    model_seconds: float = 0.0
    tool_seconds: float = 0.0
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def recall(self) -> float:
        return self.caught / (self.caught + self.missed) if self.caught + self.missed else 0.0

    @property
    def found_or_flagged(self) -> float:
        """Approvals caught, or missed but flagged "not sure" (a person is told to check). Read with false alarms."""
        total = self.caught + self.missed
        return (self.caught + self.unsure_caught) / total if total else 0.0

    @property
    def precision(self) -> float:
        return self.caught / (self.caught + self.false_alarms) if self.caught + self.false_alarms else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0


def score(cases: list[Case], predict: Predict) -> Score:
    s = Score()
    for case in cases:
        started = time.monotonic()
        pred = predict(case)
        s.seconds += time.monotonic() - started
        caught = pred.codes & case.truth
        missed = case.truth - pred.codes
        alarms = pred.codes - case.truth
        s.caught += len(caught)
        s.missed += len(missed)
        s.false_alarms += len(alarms)
        s.unsure_caught += len(pred.uncertain & missed)
        s.cost_usd += pred.cost_usd
        s.calls += pred.calls
        s.errors += pred.error is not None
        s.model_seconds += pred.model_ms / 1000
        s.tool_seconds += pred.tool_ms / 1000
        s.rows.append(
            {
                "case": case.case_id,
                "missed": sorted(missed),
                "false_alarms": sorted(alarms),
                "unsure": sorted(pred.uncertain),
                "error": pred.error,
            }
        )
    return s


def table(results: dict[str, Score], n: int) -> str:
    lines = [
        "| System | Recall | Found or flagged | Precision | F1 | Missed | False alarms | Missed but flagged 'not sure' "
        "| Model calls | Cost (USD) | Cost per event | Errors |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, s in results.items():
        per = s.cost_usd / n if n else Decimal("0")
        lines.append(
            f"| {name} | {s.recall:.2f} | {s.found_or_flagged:.2f} | {s.precision:.2f} | {s.f1:.2f} | "
            f"{s.missed} | {s.false_alarms} | "
            f"{s.unsure_caught} | {s.calls} | {s.cost_usd:.4f} | {per:.4f} | {s.errors} |"
        )
    return "\n".join(lines)
