"""One-off: writes data/forms/osa_event_proposal_2026_2027.json from the published form.

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

template = FormTemplate.model_validate(
    {"form_id": "osa_event_proposal", "version": "2026-2027", "title": "Event Proposal 2026-2027", "fields": fields}
)
out = Path("data/forms/osa_event_proposal_2026_2027.json")
out.write_text(json.dumps(template.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n")
print(f"wrote {out} ({len(template.fields)} fields)")
