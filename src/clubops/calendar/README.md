# Google Calendar setup for each club

## Current architecture boundary (20 November 2026)

The instructions above describe the implemented role-calendar adapter. D-116
supersedes that deployment design with one calendar per club and named per-event
invitees. Do not create private role calendars as a prerequisite for the new
integration. J-23 is blocked until Tatiana and Joey separately approve the
versioned calendar contract; the existing adapter remains covered by fake tests.
T-46 owns token storage/refresh, callbacks, approved-plan and cabinet triggers.

## Implemented legacy adapter reference
`CalendarSync` is a one-way copy from approved ClubOps items. Configure a **separate
Google calendar ID per club** and pass a short-lived OAuth access token to
`GoogleCalendarGateway`. Configure a **private role calendar for each cabinet role**;
only its current holder subscribes. No credentials, calendar IDs, or real event data
belong in git.

The backend can parse `CLUBOPS_GOOGLE_CALENDAR_IDS_JSON` with
`calendar_ids_from_json` and pass the returned club-to-ID map to `CalendarSync`.
The `.env.example` value stays blank. On each machine, put the actual IDs only in
private `.env` or host configuration. If an older local `.env` still uses
`CLUBOPS_GOOGLE_RUNNING_CLUB_CALENDAR_ID`, move that value privately into the
new map under `running-club`; add other clubs by slug. Never commit the map or
print it in logs. T-46 owns loading this backend setting and OAuth tokens.

1. In a Google Cloud project, enable the Calendar API and configure an OAuth consent
   screen. Create a web OAuth client for the backend's redirect URI. The backend owner
   (T-22) must store and refresh tokens server-side; the browser never receives a
   Calendar API token. Request only the Calendar events scope needed for event writes.
2. Create each club's shared calendar and private role calendars in Google Calendar.
   Store their IDs in the backend's private club configuration. Grant the connecting
   account permission to change events on all of them. The cabinet subscribes to the
   shared calendar; each role holder subscribes only to their role calendar. Change
   role-calendar access when the cabinet changes.
3. After a cabinet member approves the current plan revision, call `event_items`, then
   `CalendarSync.sync(item, approved=True, role_emails=...)` for each item. Never call it
   from page load or an unapproved plan. `SyncQueue` saves approved items in SQLite;
   drain it after approval and on a retry schedule. A `SyncError` leaves the item pending.
   Show the item as not synced until retry succeeds. Store the queue in private host data,
   outside the repository.
4. Member addresses for role checks come from the backend's private club directory.
   A missing holder sends the reminder to the president's private role calendar and
   returns `missing_roles` so Review can ask the cabinet to assign the role. Deployment
   must verify private calendar subscriptions and popup delivery with test accounts.

Google limits a normal event's reminders to offsets **before** its start. ClubOps creates
separate, stable reminder events on role calendars for before, on-day, and after-day reminders. An item
marked done keeps its main event and deletes those reminder events. Cancellation deletes
both. The sync is safe to repeat after network failures.

The implementation and fake-Google tests are ready. Live setup still needs the Cloud
project, OAuth callback, per-club calendar IDs, and a cabinet member's test approval.

Shared-calendar cabinet access can be managed by `GoogleCalendarSharing`: the backend
calls `grant_reader(calendar_id, email)` after adding a cabinet member and
`revoke_reader(calendar_id, email)` after removal. Both require a server-held token
authorized as the calendar owner with the separate `calendar.acls` scope. Reader
access does not grant ClubOps approval rights. Existing writer or owner access is
left for a person to review. Google may send a sharing notification, and the member
may still need to add the calendar to their own Calendar list. The backend API and
Settings wiring are owned by Tatiana and Christophe respectively; this adapter
does not create or refresh OAuth tokens.

API references: [Events insert](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert),
[Events update](https://developers.google.com/workspace/calendar/api/v3/reference/events/update),
[Reminders](https://developers.google.com/workspace/calendar/api/concepts/reminders).

## Live acceptance receipt (J-01/J-09/J-21)

Keep the real calendar ID, accounts, approval record and screenshots only in
ignored private storage. Publish only a dated aggregate receipt with tested
commit, environment, pass/fail per step and generic failure category. A local
adapter test is not deployed acceptance.

1. Obtain approval for the actual test event, audience and cleanup. Confirm
   separate Calendar authorization and reconnect behavior; Google sign-in alone
   grants no Calendar access.
2. Show that an unapproved/stale plan makes no Google write. Approve the current
   plan in ClubOps; verify one copy in the correct club calendar and isolation
   from a second club.
3. Repeat the sync and move the date using the same item ID. Verify one copy,
   the new date/time in Asia/Beirut and pending-to-synced status.
4. Verify only the approved audience receives the intended reminders; mark done
   and verify reminders stop. Cancel and verify the event/tasks disappear.
5. Interrupt provider access, observe pending/error without lost work, restart
   the host and retry. Confirm durable queue storage and no duplicate copy.
6. Add/remove a cabinet test member; verify reader grant/revoke and preservation
   of elevated rules. Verify audience changes separately after J-23 lands.
7. Record each result privately, clean up only approved test artifacts, and
   report unresolved token, scheduler, ACL or audience failures to the owner.

Joey's 20 November README startup attempt stopped at the prerequisite check:
`docker version` could not reach `dockerDesktopLinuxEngine` (named pipe absent).
Starting the installed Docker Desktop app made its engine pipe available, but the
version API then returned HTTP 500. No fresh Compose startup, browser login or
hosted persistence outcome is claimed.
