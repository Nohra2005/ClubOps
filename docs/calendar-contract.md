# Calendar contract (event plan → Google Calendar)

The code version is `src/clubops/contracts/calendar.py` (`CalendarItem`), exported as `schemas/calendar-items.response.json`. A test checks that the example below is valid, so this page and the code cannot drift apart.

What the backend gives the calendar part, and what the calendar part does with it. Owner of the calendar part: Joey (TASKS.md J-01 to J-09). Owner of the plan side: Tatiana (T-13, T-14). Decided 2026-10-22 (design log D-45).

## Rules

1. **ClubOps is the boss.** Google Calendar is a copy. Changes are made in ClubOps; an edit made in Google is overwritten at the next sync.
2. **Only approved plans, or trusted mail.** Event items are sent after a cabinet member approves the plan, never before. Deadline tasks from an OSA e-mail are added without a click, but only when the mail passed every check (D-138, below).
3. **One ID, one item.** `item_id` never changes. Sending the same `item_id` again updates the item; it never makes a duplicate.
4. **Reminders go to the role holder.** The person who holds `owner_role` gets the reminder; everyone sees the shared club calendar. `all_cabinet` means every cabinet member.

## A calendar item

| Field | Type | Example | Notes |
|---|---|---|---|
| `item_id` | string | `ev-triathlon-2026/book-hostler` | stable; `<event_id>/<task>`, or `club/<name>` for club-wide items |
| `club_id` | string | `running-club` | |
| `event_id` | string or null | `ev-triathlon-2026` | null for club-wide reminders |
| `kind` | `event` \| `task` | `task` | |
| `title` | string | `Ask Hostler for access to track and pool` | |
| `date` | date | `2026-10-04` | tasks: all-day on this date |
| `start`, `end` | datetime or null | `2026-10-18T06:00+03:00` | events only, time-zone aware (Asia/Beirut) |
| `owner_role` | role or `all_cabinet` | `events` | |
| `reminders` | list | see defaults | each: `{"before_days": 2}`, `{"on_day_at": "08:00"}` or `{"after_days": 2}` |
| `repeat_until_done` | bool | `true` | the impact form only: remind again if still open |
| `link` | URL | `https://…/events/triathlon-2026` | opens the item in ClubOps |
| `status` | `open` \| `done` \| `cancelled` | `open` | |
| `origin` | `plan` \| `mail` \| `person` | `mail` | where it came from (default `plan`) |
| `source_ref` | string or null | `kh-mid-year-eval` | the fact a mail deadline came from; required when `origin` is `mail` |
| `edited_by_person` | bool | `false` | a person changed it; later mail never overwrites it |

## Default reminders

| Item | Reminders |
|---|---|
| Task | 2 days before, and 08:00 on the day |
| Event | 1 day before |
| Impact form | 2 days after the event, again 5 days after if not done |
| OSA rule check (club-wide) | first of each month from September, until the president marks the new rules as in |
| Cabinet elections (club-wide) | 1 April |

## What the calendar part does

| It receives | It does |
|---|---|
| A new `item_id` | creates the item with its reminders |
| A known `item_id`, changed fields | updates it (e.g. moves the date) |
| `status: done` | keeps the item, removes its reminders |
| `status: cancelled` | deletes it |
| An event cancelled | the backend sends `cancelled` for the event and all its tasks |

## Failure cases (each gets a Failure Matrix row)

- Google unreachable: retry later; ClubOps shows "not synced" on the Calendar screen; nothing is lost.
- The same item sent twice: no duplicate (rule 3).
- A role nobody holds: the item is created, the reminder goes to the president, and Review shows "nobody holds this role".

## Example

Planning "Sprint Triathlon, 18 Oct" and approving the plan sends one event and its tasks, for example:

```json
[
  {"item_id": "ev-triathlon-2026/event", "club_id": "running-club", "event_id": "ev-triathlon-2026",
   "kind": "event", "title": "AUB Sprint Triathlon", "date": "2026-10-18",
   "start": "2026-10-18T06:00:00+03:00", "end": "2026-10-18T12:00:00+03:00",
   "owner_role": "all_cabinet", "reminders": [{"before_days": 1}], "status": "open"},
  {"item_id": "ev-triathlon-2026/book-hostler", "club_id": "running-club", "event_id": "ev-triathlon-2026",
   "kind": "task", "title": "Ask Hostler for access to track and pool", "date": "2026-10-04",
   "owner_role": "events", "reminders": [{"before_days": 2}, {"on_day_at": "08:00:00"}], "status": "open"},
  {"item_id": "ev-triathlon-2026/impact-form", "club_id": "running-club", "event_id": "ev-triathlon-2026",
   "kind": "task", "title": "Fill the OSA impact report", "date": "2026-10-20",
   "owner_role": "president", "reminders": [{"after_days": 2}, {"after_days": 5}],
   "repeat_until_done": true, "status": "open"},
  {"item_id": "club/osa-rule-check-2026-09", "club_id": "running-club", "event_id": null,
   "kind": "task", "title": "Check the OSA rules page for this year's update", "date": "2026-09-01",
   "owner_role": "president", "reminders": [{"on_day_at": "09:00:00"}], "status": "open"}
]
```


## Deadlines from trusted OSA mail (contract 0.3.0, D-138)

The reader finds a deadline in a verified OSA e-mail. It becomes calendar tasks with no approval click. A person can edit or remove each task afterwards. Owner of the code that reads the mail: Tatiana. Owner of the calendar side: Joey.

**Who gets the task.** The cabinet role(s) named on the deadline, taken from the role descriptions. Each role gets its own task (`club/dl-<hash of source_ref>-<role>`) with that role's holder as owner. Nobody is added by name and nobody outside the cabinet is ever invited. If two roles need the same deadline, two tasks exist; nothing is shared. A role nobody holds follows the existing fallback (the president).

**What goes in** (`DeadlineTasksRequest` → `DeadlineItems`, built by `clubops.calendar.items.deadline_items`):

| Field | Meaning |
|---|---|
| `trusted` | the mail passed every check: verified forwarder, OSA sender on the list, no hidden instructions, not outdated. If false, the function refuses |
| `tasks[]` | `title`, `date`, `owner_roles` (1 to 4 cabinet roles, each once), `source_ref` (the fact id) |
| `existing[]` | the club's mail items already on the calendar, so edited ones are recognised |

**What comes out:** `items` (to sync like any other item) and `held` (not added; Review shows each with its reason).

**Safeguards (each one has a Failure Matrix row)**

| Case | What happens |
|---|---|
| Mail did not pass every check | no task; the card goes to Review as before |
| Same fact arrives again, or a later mail moves the date | same `item_id`, so the task is updated, never duplicated |
| A person edited the task (`edited_by_person`) | the task is kept as the person left it; the new date is `held` as `edited_by_person` |
| Date in the past, or more than 366 days ahead | `held` as `past_date` / `too_far` |
| More than 10 deadlines in one mail | none added; all `held` as `too_many` |
| Wrong task | a person edits it (`origin: person`, `edited_by_person: true`) or removes it (`status: cancelled`, rule above) |

Reminders are the task default: 2 days before and 08:00 on the day. The model never sets them.

**Not in this contract:** a list of invitees, an "add to calendar" tick, a second approval. Calendar scopes and the per-club calendar stay as in D-116.
