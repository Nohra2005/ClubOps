"""Build data/rulebook/aub-rules.json: the AUB-wide rules every club and society follows (T-08).

Each rule comes from a public AUB/OSA document (or, where marked, from the Running Club president)
and quotes the line it rests on. A cabinet member read every rule before it was marked verified; after
any change here, the reviewer reads the changed rules again and updates REVIEWER / REVIEWED_AT.

Run: uv run python scripts/build_rulebook.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUT = Path("data/rulebook/aub-rules.json")
SEEN = "2026-10-12T12:00:00+03:00"
REVIEWER = "m-tatiana-nohra"  # Running Club president; read all 25 rules on 2026-10-23
REVIEWED_AT = "2026-10-23T22:49:00+03:00"

FIN = ("document", "osa-financial-policy", "aub.edu.lb/SAO/activities/Documents/Financial Policy.pdf")
POSTERS = ("document", "osa-poster-policy", "aub.edu.lb/SAO/activities/Documents/poster-policy.pdf")
REQUEST = ("document", "osa-activity-request", "aub.edu.lb/SAO/activities/Documents/poster-display-request.pdf")
FORM = ("form", "osa-event-proposal-2026-2027", "Microsoft Form, Event Proposal 2026-2027")
USFC = ("document", "usfc-funding", "aub.edu.lb/SAO/activities/Pages/USFCFunding.aspx")
SPORTS = ("document", "aub-sports-facilities-guidelines", "AUB policytech docid 1571")
COMMS = ("document", "aub-online-communication-policy", "AUB policytech docid 2988")
DIGITAL = ("document", "aub-communications-digital", "aub.edu.lb/communications/Pages/digital.aspx")
ROOMS = ("document", "osa-room-reservation", "aub.edu.lb/SAO/activities/Pages/RoomReservation.aspx")
IMPACT = ("form", "osa-impact-report-2026-2027", "Microsoft Form, Post-Event Impact Report 2026/27")
PRESIDENT = ("user_input", "running-club-president-2026-10", "stated by the Running Club president")

Source = tuple[str, str, str]


def req(rid: str, kind: str, name: str, lead: int | None = None, working: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"requirement_id": rid, "kind": kind, "name": name}
    if lead is not None:
        out["lead_time_days"] = lead
    if working:
        out["working_days"] = True
    return out


def rule(  # noqa: PLR0917 (one row of data per call)
    code: str,
    slug: str,
    title: str,
    statement: str,
    triggers: list[str],
    reqs: list[dict[str, Any]],
    sources: list[tuple[Source, str]],
    tags: list[str],
) -> dict[str, Any]:
    refs = [
        {"kind": s[0], "source_id": s[1], "locator": s[2], "quote": quote, "observed_at": SEEN} for s, quote in sources
    ]
    return {
        "item_id": f"kh-aub-{slug}",
        "scope": "aub",
        "club_id": None,
        "title": title,
        "statement": statement,
        "details": {"kind": "rule", "triggers": triggers, "requirements": reqs},
        "tags": [*tags, code.lower()],
        "sources": refs,
        "support": {"events": [], "source_count": len(refs)},
        "status": "verified",
        "verified_by": REVIEWER,
        "verified_at": REVIEWED_AT,
        "version": 1,
    }


TWO_WEEKS = 10  # "2 weeks before the event, excluding weekends/holidays" = 10 working days

RULES = [
    rule(
        "PROP",
        "proposal",
        "Every event needs an OSA event proposal",
        "Every club or society event needs the OSA Event Proposal form, at least 2 weeks before the event, "
        "not counting weekends and holidays.",
        ["always"],
        [req("osa-proposal", "form", "OSA event proposal (online form)", TWO_WEEKS, True)],
        [
            (
                FIN,
                "Finalized Expense form + Student Activity/Poster Display Request ... >= 2 weeks before the "
                "event, excluding weekends/holidays",
            ),
        ],
        ["proposal"],
    ),
    rule(
        "ADV",
        "adviser",
        "The adviser approves every proposal",
        "The club's adviser must approve the proposal; the form sends it to the adviser's AUB e-mail.",
        ["always"],
        [req("adviser-approval", "approval", "Adviser approves the proposal", TWO_WEEKS, True)],
        [(FORM, "Adviser's AUB Email ... otherwise your form won't be submitted correctly to your adviser")],
        ["proposal", "adviser"],
    ),
    rule(
        "EXP",
        "expense-form",
        "Anything the club pays for goes on the expense form",
        "All expenses need OSA approval before any commitment: fill the expense form and upload it with the "
        "proposal. Items given by sponsors are not listed on it. Buying something also needs a proposal.",
        ["expenses"],
        [req("expense-form", "form", "Expense form uploaded with the proposal", TWO_WEEKS, True)],
        [
            (FIN, "All revenues/expenses (monetary or not) need OSA approval before any commitment."),
            (PRESIDENT, "sponsors are not included on the expense form"),
        ],
        ["money"],
    ),
    rule(
        "RCPT",
        "receipts",
        "Receipts within 1 week after the event",
        "Receipts and invoices go to Student Activities within 1 week after the event; after 4 weeks they are "
        "rejected.",
        ["expenses"],
        [req("receipts", "document", "Receipts and invoices within 1 week after the event")],
        [(FIN, "Receipts/invoices within 1 week after the event; after 4 weeks automatically rejected.")],
        ["money", "after-event"],
    ),
    rule(
        "VOTE",
        "majority-vote",
        "Spending over $200 needs a members' vote",
        "Expenses over $200 need a majority vote of the members, recorded in minutes and submitted with the proposal.",
        ["budget_over_200"],
        [req("majority-vote", "document", "Minutes of the members' majority vote", TWO_WEEKS, True)],
        [
            (
                FIN,
                "Expenses over $200 need a majority vote of members, recorded in minutes, submitted with the proposal.",
            )
        ],
        ["money"],
    ),
    rule(
        "MAJOR",
        "major-event",
        "Major events need 6 weeks",
        "Major events (conferences, gala dinners, rally paper, or a budget over $1,000) are submitted at least "
        "6 weeks before.",
        ["major_event"],
        [req("major-lead-time", "lead_time", "Submit the proposal 6 weeks before (major event)", 42)],
        [(FIN, "Major events (conferences, gala dinners, rally paper, or budget > $1,000): >= 6 weeks before.")],
        ["proposal", "money"],
    ),
    rule(
        "SPON",
        "sponsor-document",
        "Sponsors need a sponsorship document",
        "Each sponsor needs a document stating the type of sponsorship (money, goods, discount, vouchers, "
        "service) and what the sponsor gets; money also states timing and method.",
        ["external_sponsor"],
        [req("sponsor-document", "document", "Sponsorship document (type + what the sponsor gets)", TWO_WEEKS, True)],
        [
            (
                FIN,
                "Sponsor documents state the sponsorship type (money, goods, discount, vouchers, service) and the "
                "return (e.g. logo)",
            )
        ],
        ["sponsors"],
    ),
    rule(
        "NOBAN",
        "sponsor-ban",
        "No energy-drink, alcohol, tobacco or bar sponsors",
        "Sponsors may not be related to energy drinks, alcohol, cigarettes or bars.",
        ["external_sponsor"],
        [req("sponsor-check", "restriction", "Check no sponsor is an energy drink, alcohol, cigarette or bar brand")],
        [(FIN, "No sponsors related to energy drinks, alcohol, cigarettes or bars.")],
        ["sponsors"],
    ),
    rule(
        "PRIZE",
        "prizes",
        "Prizes: winners e-mailed, no cash",
        "Prizes go on the expense form; after the event, e-mail the winners' names, IDs, contacts and amounts. "
        "No cash handling.",
        ["prizes"],
        [req("prize-winners", "document", "E-mail winners' names, IDs and amounts; prizes on the expense form")],
        [
            (
                FIN,
                "Prizes: email with winners' names, IDs, contacts, amounts; no cash handling; "
                "prizes in the Expense form.",
            )
        ],
        ["prizes"],
    ),
    rule(
        "POST",
        "poster-approval",
        "Posters and flyers need the OSA stamp",
        "Posters need OSA approval and a stamp before posting (official boards only, max A3, 75 per event); "
        "flyer distribution needs approval in advance. Sponsor logos max 3 x 3 cm.",
        ["publicity"],
        [req("poster-approval", "approval", "OSA approval and stamp for posters and flyers", TWO_WEEKS, True)],
        [(POSTERS, "OSA approval + stamp before posting; submitted to West Hall 112.")],
        ["publicity"],
    ),
    rule(
        "LOGO",
        "logo-use",
        "No AUB logo without Communications approval",
        "AUB's logo or branding may not be used without prior approval from the Office of Communications. "
        "Logos of non-AUB entities are not put on club material.",
        ["publicity"],
        [req("logo-check", "restriction", "No AUB logo without Communications approval; no non-AUB logos")],
        [
            (
                COMMS,
                "AUB's logo or other branding elements may NOT be used in digital communication without prior "
                "approval from the Office of Communications.",
            ),
            (PRESIDENT, "Non-AUB entities may not have a logo on club material."),
        ],
        ["publicity", "design"],
    ),
    rule(
        "EMAIL",
        "no-mass-email",
        "Mass e-mail may not promote events",
        "Mass e-mail may not promote events or send reminders; use the events website, newsletter, campus "
        "screens or social media.",
        ["publicity"],
        [req("no-mass-email", "restriction", "Promote through the events site, screens or social media")],
        [(DIGITAL, "Mass email may NOT promote events (no reminders either).")],
        ["publicity"],
    ),
    rule(
        "HOST",
        "hostler-booking",
        "Hostler facilities are requested 2 weeks ahead",
        "Hostler / CHSC facilities (Green Field, track, pool, courts) are requested at least 2 weeks ahead; "
        "clubs come last in priority and may be bumped; one supervisor per 20 participants.",
        ["hostler_venue"],
        [req("hostler-booking", "approval", "Hostler / CHSC facility request", 14)],
        [(SPORTS, "Exclusive use: request >= 2 weeks ahead through the director of university sports")],
        ["venue", "sports"],
    ),
    rule(
        "ROOM",
        "room-booking",
        "Rooms are reserved through WebReserve",
        "Rooms for an event are reserved through AUB WebReserve (West Hall auditoriums A, B, C, Bathish, room 310).",
        ["indoor_room"],
        [req("room-booking", "approval", "Reserve the room on WebReserve", TWO_WEEKS, True)],
        [
            (FORM, "For facility reservation, please refer to the following link: webreserve"),
            (ROOMS, "Click here to reserve any room"),
        ],
        ["venue"],
    ),
    rule(
        "GUEST",
        "non-aub-guests",
        "Non-AUB guests need approval and a list of names",
        "Guests from outside AUB need approval; attach an Excel list of their names to the proposal.",
        ["non_aub_guests"],
        [req("guest-approval", "approval", "Approval for non-AUB guests + Excel list of names", TWO_WEEKS, True)],
        [
            (REQUEST, "Non-AUB community guests require approval."),
            (FORM, "For non-AUB guests, please provide a list of their names in an excel file"),
        ],
        ["guests"],
    ),
    rule(
        "TICK",
        "tickets",
        "Tickets and fees: list of participants and payments",
        "Ticketed events, trips and tournaments need an Excel of participants with tracking numbers and the "
        "amount each paid.",
        ["tickets"],
        [req("ticket-list", "document", "Excel of participants, tracking numbers and amounts paid")],
        [(FIN, "Ticketed events / trips / tournaments: Excel of participants, tracking numbers, amount paid each.")],
        ["money"],
    ),
    rule(
        "COLLAB",
        "collaboration",
        "Partner clubs: state the split",
        "Events with other student organizations or departments state how expenses and revenues are split.",
        ["partner_club"],
        [req("collab-split", "document", "Expense and revenue split with the partner", TWO_WEEKS, True)],
        [(FIN, "Collaboration with other student orgs/departments: state the expense/revenue split.")],
        ["partners"],
    ),
    rule(
        "EXT",
        "external-org",
        "External organizations: overview and split",
        "Events with an NGO or other non-AUB organization include an overview of it, its role and the expense "
        "split. External NGOs generally may not use clubs for fundraising.",
        ["external_org"],
        [
            req(
                "external-overview",
                "document",
                "Overview of the external organization, its role and the split",
                TWO_WEEKS,
                True,
            )
        ],
        [(FIN, "Collaboration with NGOs / non-AUB entities: overview of the entity, its role, the expense split.")],
        ["partners"],
    ),
    rule(
        "SPEAK",
        "speakers",
        "Speakers: details and CV, free of charge",
        "Public speakers need first name, last name, nationality, subject and a brief CV; speakers and "
        "performers must be free of charge.",
        ["speaker"],
        [req("speaker-details", "document", "Speaker names, nationality, subject and CV", TWO_WEEKS, True)],
        [
            (
                FORM,
                "please provide the following (First Name, Last Name, Nationality), the subject of their talk "
                "and attach a brief CV",
            ),
            (FIN, "Speakers/performers must be free of charge."),
        ],
        ["speakers"],
    ),
    rule(
        "FOOD",
        "food",
        "Food and drinks: list items and suppliers",
        "Events with food or drinks list the items and suppliers, using the procurement set menus; OSA sets a "
        "food ceiling per event type.",
        ["catering"],
        [req("food-list", "document", "List of food items and suppliers (procurement set menus)", TWO_WEEKS, True)],
        [
            (FORM, "please provide the list of items and the corresponding suppliers"),
            (FIN, "Food ceiling set by OSA per event type."),
        ],
        ["food"],
    ),
    rule(
        "SAFE",
        "safety",
        "Risky activities need an EHSRM safety recommendation",
        "Some activities (water, big crowds, roads, physical risk) need a safety recommendation signed by an "
        "EHSRM safety officer.",
        ["risky_activity"],
        [req("safety-recommendation", "approval", "EHSRM safety recommendation", TWO_WEEKS, True)],
        [(REQUEST, "Some activities need an EHSRM (safety) recommendation.")],
        ["safety"],
    ),
    rule(
        "FILM",
        "filming",
        "Official filming needs Communications approval",
        "Official filming or photography on AUB premises to promote an event needs Office of Communications "
        "authorization and consent of identifiable people.",
        ["filming"],
        [
            req(
                "filming-approval",
                "approval",
                "Communications authorization for filming + consent forms",
                TWO_WEEKS,
                True,
            )
        ],
        [
            (
                COMMS,
                "Official filming/photography on AUB premises to promote AUB programs or events ... needs "
                "Office of Communications authorization",
            )
        ],
        ["publicity"],
    ),
    rule(
        "USFC",
        "usfc",
        "USFC money: no catering, prizes or salaries",
        "USFC funding needs the event approved first and cannot pay for catering, prizes or salaries; it must be "
        "disclosed in publicity.",
        ["usfc"],
        [req("usfc-limits", "restriction", "USFC money cannot pay for catering, prizes or salaries")],
        [(USFC, "Event must be AUB-approved first; no catering, no prizes, no salaries")],
        ["money"],
    ),
    rule(
        "FUND",
        "fundraiser",
        "Fundraisers prove payment to the beneficiary",
        "Fundraisers include proof of payment to the beneficiary in the impact report.",
        ["fundraiser"],
        [req("fund-proof", "document", "Proof of payment to the beneficiary (in the impact report)")],
        [(IMPACT, "funds raised, proof of payment to beneficiary (fundraisers)")],
        ["money", "after-event"],
    ),
    rule(
        "IMPACT",
        "impact-report",
        "Impact report after every event",
        "After every event, fill the Post-Event Impact Report (attendees, impact, lessons learned, photos).",
        ["always"],
        [req("impact-report", "form", "Post-Event Impact Report after the event")],
        [(IMPACT, "Impact: attendees, impact on club, goal achieved, LESSONS LEARNED")],
        ["after-event"],
    ),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(RULES, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(RULES)} rules to {OUT}")


if __name__ == "__main__":
    main()
