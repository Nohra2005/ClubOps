"""One-off: writes data/forms/osa_event_proposal_2026_2027.json from the published form.

Field ids are stable (q01-q33 = the form with every "No"); questions the live form adds after a "Yes"
(materials, catering) are q34-q52, placed after the question that opens them. Checked against a
print of the live form with every branch open (2026-10-31): 52 questions.

Kept in the repo so the transcription can be reviewed against the form, field by field.
"""

import json
from pathlib import Path

from clubops.contracts.forms import FormTemplate

YES_NO = ["Yes", "No"]
EVENT_TYPES = [
    "Conference",
    "Community Service Event",
    "Concert",
    "Debate",
    "Exhibition",
    "Film Screening",
    "Gala Dinner",
    "Lecture",
    "Meeting",
    "Play",
    "Reception",
    "Sport",
    "Trip",
    "Workshop",
    "Other",
]
SDGS = [
    "SDG 1: No Poverty",
    "SDG 2: Zero Hunger",
    "SDG 3: Good Health and Well-Being",
    "SDG 4: Quality Education",
    "SDG 5: Gender Equality",
    "SDG 6: Clean Water and Sanitation",
    "SDG 7: Affordable and Clean Energy",
    "SDG 8: Decent Work and Economic Growth",
    "SDG 9: Industry, Innovation, and Infrastructure",
    "SDG 10: Reduced Inequalities",
    "SDG 11: Sustainable Cities and Communities",
    "SDG 12: Responsible Consumption and Production",
    "SDG 13: Climate Action",
    "SDG 14: Life Below Water",
    "SDG 15: Life on Land",
    "SDG 16: Peace, Justice, and Strong Institutions",
    "SDG 17: Partnership for the Goals",
]


def f(n, label, type_, required, source, **kw):
    return {"field_id": f"q{n:02d}", "label": label, "type": type_, "required": required, "source": source, **kw}


fields = [
    f(1, "Club/Society Name", "text", True, "profile.form_name"),
    f(2, "If your Club/Society is not listed, please indicate the Club/Society name", "text", False, "human"),
    f(3, "Requester's First Name", "text", True, "requester.first_name"),
    f(4, "Requester's Last Name", "text", True, "requester.last_name"),
    f(5, "Requester's AUB ID number", "aub_id", True, "requester.aub_id", sensitive=True),
    f(6, "Requester's Position in the Club/Society", "text", True, "requester.role"),
    f(7, "Requester's AUB E-mail", "email", True, "requester.aub_email"),
    f(8, "Requester's Phone", "phone", True, "requester.phone", sensitive=True),
    f(9, "Event/Activity Title", "text", True, "event.title"),
    f(10, "Event/Activity Type", "single_choice", True, "event.event_type", choices=EVENT_TYPES),
    f(
        11,
        "If you chose other, please specify",
        "text",
        False,
        "event.event_type_other",
        required_if={"field_id": "q10", "equals": "Other"},
    ),
    f(
        12,
        "Which of the 17 SDGs does your event/activity contribute to?",
        "multi_choice",
        False,
        "event.sdgs",
        choices=SDGS,
        help="The published form lists SDG 4 twice; it is recorded once here.",
    ),
    f(
        13,
        "Event Starting Date",
        "date",
        True,
        "event.start",
        help="Please book the studentactivities@aub.edu.lb Outlook calendar by sending a calendar invitation",
    ),
    f(14, "Event Starting Time (Enter time in 24-hour format, e.g. 13:00)", "time_24h", True, "event.start"),
    f(15, "Event Ending Date", "date", True, "event.end"),
    f(16, "Event Ending Time (Enter time in 24-hour format, e.g. 13:00)", "time_24h", True, "event.end"),
    f(
        17,
        "Event Location",
        "text",
        True,
        "event.venue",
        help="For facility reservation, please refer to https://www.aub.edu.lb/AboutUs/Pages/webreserve.aspx",
    ),
    f(
        18,
        "Please briefly describe your activity, including all pertinent details",
        "long_text",
        True,
        "event.description",
    ),
    f(
        19,
        "Do you require any materials for your event (e.g., chairs, tables, boards, tents, etc.)?",
        "single_choice",
        True,
        "event.needs_materials",
        choices=YES_NO,
    ),
    f(
        20,
        "Does your event include catering?",
        "single_choice",
        True,
        "event.has_catering",
        choices=YES_NO,
        help="If yes, refer to the Procurement Set Menus",
    ),
    f(
        21,
        "If the activity involves public speakers, provide first name, last name, nationality, subject of the talk, "
        "and attach a brief CV of each",
        "file",
        False,
        "attachment.speaker_cv",
        max_files=10,
    ),
    f(
        22,
        "Is this event open to AUB students only or AUB students and non-AUB students "
        "(non-AUB community guests require approval)?",
        "single_choice",
        True,
        "event.audience",
        choices=["AUB students only", "AUB students and Non-AUB students"],
    ),
    f(23, "Approximate number of guests expected to attend", "count_range", True, "event.expected_attendance"),
    f(
        24,
        "For non-AUB guests, provide a list of their names in an Excel file",
        "file",
        False,
        "attachment.guest_list",
        max_files=1,
        required_if={"field_id": "q22", "equals": "AUB students and Non-AUB students"},
    ),
    f(
        25,
        "Admission to the event is",
        "single_choice",
        True,
        "event.admission",
        choices=["Free Entry", "By ticket", "Not applicable"],
    ),
    f(
        26,
        "If admission is by ticket, indicate the ticket price with the currency",
        "text",
        False,
        "event.ticket_price",
        required_if={"field_id": "q25", "equals": "By ticket"},
    ),
    f(
        27,
        "How do you plan to cover the expenses of your event?",
        "multi_choice",
        True,
        "event.funding",
        choices=["Club Account", "External Sponsor", "Faculty/Department Aid", "USFC", "No expenses"],
        help="Single or multiple choice is not visible on the printed form; to confirm on the live form.",
    ),
    f(
        28,
        "If your event includes a reception with food and beverages, list the items and suppliers",
        "long_text",
        False,
        "event.catering_items",
        required_if={"field_id": "q20", "equals": "Yes"},
    ),
    f(
        29,
        "Upload any poster, ad, brochure or other promotional material",
        "file",
        False,
        "attachment.poster",
        max_files=5,
    ),
    f(
        30,
        "Download the Expense form, complete it and upload it here",
        "file",
        False,
        "attachment.expense_form",
        max_files=5,
    ),
    f(
        31,
        "Provide a confirmation if the event is funded by an external sponsor, faculty/department aid, or USFC",
        "file",
        False,
        "attachment.funding_confirmation",
        max_files=1,
    ),
    f(32, "Adviser's Name (first and last name, no prefix such as Dr. or Prof.)", "text", True, "profile.adviser.name"),
    f(33, "Adviser's AUB Email", "email", True, "profile.adviser.aub_email"),
]

DROPDOWN = "a dropdown on the live form; its choices were not captured, so any whole number is accepted"


def yes(parent: str) -> dict[str, str]:
    return {"field_id": parent, "equals": "Yes"}


MATERIALS = [
    f(
        34,
        "Number of tables required",
        "count_range",
        False,
        "event.materials.tables",
        required_if=yes("q19"),
        help=DROPDOWN,
    ),
    f(
        35,
        "Number of chairs required",
        "count_range",
        False,
        "event.materials.chairs",
        required_if=yes("q19"),
        help=DROPDOWN,
    ),
    f(
        36,
        "Number of boards required",
        "count_range",
        False,
        "event.materials.boards",
        required_if=yes("q19"),
        help=DROPDOWN,
    ),
    f(
        37,
        "Do you require tents for your event?",
        "single_choice",
        False,
        "event.materials.needs_tents",
        choices=YES_NO,
        required_if=yes("q19"),
    ),
    f(
        38,
        "Number of tents required",
        "count_range",
        False,
        "event.materials.tents",
        required_if=yes("q37"),
        help=DROPDOWN,
    ),
    f(
        39,
        "Do you require table covers?",
        "single_choice",
        False,
        "event.materials.needs_table_covers",
        choices=YES_NO,
        required_if=yes("q19"),
    ),
    f(
        40,
        "Number of table covers required",
        "count_range",
        False,
        "event.materials.table_covers",
        required_if=yes("q39"),
        help=DROPDOWN,
    ),
    f(
        41,
        "Do you require electrical outlets for your event?",
        "single_choice",
        False,
        "event.materials.needs_outlets",
        choices=YES_NO,
        required_if=yes("q19"),
    ),
    f(
        42,
        "What is the required amperage (in amps)?",
        "text",
        False,
        "event.materials.amperage",
        required_if=yes("q41"),
    ),
    f(
        43,
        "How many electrical outlets will you need?",
        "count_range",
        False,
        "event.materials.outlets",
        required_if=yes("q41"),
        help=DROPDOWN,
    ),
]
CATERING = [
    f(44, "Catering Menu (Caterer - Menu)", "text", False, "event.catering.menu", required_if=yes("q20")),
    f(
        45,
        "Exact number of people who should be considered for catering (a number, not a range)",
        "count_range",
        False,
        "event.catering.people",
        required_if=yes("q20"),
    ),
    f(46, "Catering Setup time", "text", False, "event.catering.setup_time", required_if=yes("q20")),
    f(
        47,
        "Price per person",
        "text",
        False,
        "event.catering.price_per_person",
        required_if=yes("q20"),
        help="The live form accepts a number only",
    ),
    f(
        48,
        "Do you need an additional catering option?",
        "single_choice",
        False,
        "event.catering.needs_second_option",
        choices=YES_NO,
        required_if=yes("q20"),
    ),
    f(49, "Catering Option 2 (Caterer - Menu)", "text", False, "event.catering.second.menu", required_if=yes("q48")),
    f(
        50,
        "Exact number of people who should be considered for catering 2 (a number, not a range)",
        "count_range",
        False,
        "event.catering.second.people",
        required_if=yes("q48"),
    ),
    f(
        51,
        "Price per person (catering 2)",
        "text",
        False,
        "event.catering.second.price_per_person",
        required_if=yes("q48"),
        help="The live form accepts a number only",
    ),
    f(
        52,
        "Will the catering cost be shared with other clubs or societies? "
        "If yes, list all clubs/societies splitting the cost (including yours)",
        "text",
        False,
        "event.catering.shared_with",
        required_if=yes("q20"),
    ),
]


def with_branches(base: list[dict]) -> list[dict]:
    out = []
    for field in base:
        out.append(field)
        out.extend({"q19": MATERIALS, "q20": CATERING}.get(field["field_id"], []))
    return out


template = FormTemplate.model_validate(
    {
        "form_id": "osa_event_proposal",
        "version": "2026-2027",
        "title": "Event Proposal 2026-2027",
        "fields": with_branches(fields),
    }
)
out = Path("data/forms/osa_event_proposal_2026_2027.json")
out.write_text(json.dumps(template.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n")
print(f"wrote {out} ({len(template.fields)} fields)")
