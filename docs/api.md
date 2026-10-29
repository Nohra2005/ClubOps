# Backend API (T-22) — what the web app can call

Code: `src/clubops/api/`. Tests: `tests/test_api.py`. Interactive list of endpoints: `/api/docs` on a running server.

Run it locally (dev sign-in on, no Google, recorded/fake model):

```bash
CLUBOPS_DEV_LOGIN=1 CLUBOPS_COOKIE_SECURE=0 uv run uvicorn clubops.api.app:build --factory --reload
uv run python scripts/load_rulebook.py --data-dir data/app      # the 25 AUB rules
uv run python scripts/add_member.py running-club "Your Name" you@mail.aub.edu president
```

## Conventions (answers to `web/API_NOTES.md`)

| Topic | Decision |
|---|---|
| Response shape | Bare JSON, no `Result` envelope. Screens get the view models of `web/src/api/types.ts`; `/api/runs/*` returns the `AgentRun` contract as is (`schemas/plan-event.response.json`). |
| Errors | HTTP status + `{"detail": "<plain sentence>"}`: 401 not signed in, 403 not allowed (or missing header), 404 not found (also another club's data), 409 changed since loaded, 422 bad input, 501 not built yet. |
| CSRF | **Every** POST, PATCH and DELETE needs `X-Requested-With: ClubOps`, including bodiless POSTs (`rebuild`, `continue`) and file uploads. The frontend now sends it in all these cases; the browser sets multipart boundaries. |
| Sign-in | Google (D-56), any Google account: AUB accounts are Microsoft, and Microsoft sign-in would need AUB IT's approval, so the president puts each member's Google e-mail on the cabinet list (D-68). The browser gets Google's ID token (Google Identity Services, client id from `CLUBOPS_GOOGLE_CLIENT_ID`) and posts it to `POST /api/auth/google {credential}`. The server checks it with Google and matches the e-mail to the cabinet list. Session = HttpOnly, SameSite=Lax cookie, 7 days. `POST /api/auth/logout` ends it. `POST /api/auth/dev {email}` exists only when `CLUBOPS_DEV_LOGIN=1`. |
| Who may do what | Any signed-in member of the club can read. Cabinet roles can plan, answer, edit, approve and decide reviews. The adviser reads only. Only the president changes the cabinet list. Ordinary members have no account. |
| Club | Always from the session, never from the URL. Another club's ids return 404. |
| Ids in paths | `task_id` contains a slash (`ev-x/osa-proposal`); both `%2F` and a raw slash work. |
| Starting a plan | `POST /api/events/plan` answers 202 `{run_id}` at once and the agent runs in the background. Poll `GET /api/runs/{run_id}`; before the first step it shows `status: running` with no steps. |
| Questions | The agent asks plain text questions (`steps[-1].state == "question"`, text in `steps[-1].text`). Answer with `POST /api/runs/{id}/answer {text}`; the response is the updated run. The structured "details" confirmation in the demo is not in the backend: send the edited details as plain text, or edit them on the event page (PATCH) afterwards. |
| Limits | At 8 steps or $0.05 the run stops with `status: at_limit`. `POST /api/runs/{id}/continue` gives one more allowance only when the user clicks it. There is no "stop": an `at_limit` run simply stays stopped. |
| Approving | `POST /api/events/{id}/approve-plan {revision}`. 409 if the details changed after the plan (`plan_outdated: true`) or the revision is old. On success the event is `approved` and its calendar items exist (`GET /api/calendar`). |

## Endpoints

| Screen | Method and path | Status |
|---|---|---|
| All | `GET /api/me` | live (`setup_complete` is always true until T-20) |
| Events | `GET /api/events` | live |
| Events | `POST /api/events/plan {description}` | live (202, background) |
| Events | `GET /api/runs/{run_id}` | live |
| Events | `POST /api/runs/{run_id}/answer {text}` | live |
| Events | `POST /api/runs/{run_id}/continue` | live (new path, not in the UI spec) |
| Events | `GET /api/events/{id}` | live; `proposal`, `drafts`, `tips`, `leaders`, `route` are empty until T-16 / J-07; no nested `agent_run` (use the run endpoint) |
| Events | `PATCH /api/events/{id} {fields}` | live for title, date, time, end_time, venue, audience (`AUB students only` / `AUB and outside guests`), has_prizes, catering (`yes`/`no`), description |
| Events | `POST /api/events/{id}/rebuild` | live (202, background) |
| Events | `POST /api/events/{id}/approve-plan {revision}` | live |
| Events | `PATCH /api/tasks/{task_id} {state, owner_role}` | live |
| Events | `POST /api/events/{id}/drafts/{type}` | 501 until J-07 is wired |
| Events | `POST /api/events/{id}/after-event {answers}` | live: closes the event, sends the facts to Review, returns `{draft, review_count}` (a plain impact-report draft until J-07) |
| Chat | `POST /api/chat/ask {text}` | placeholder: always "not known, ask the club president" until T-17 |
| Chat | `POST /api/chat/teach {text}` | live: returns `{kind: "learned", text, review_id}`; `review_id` is empty when no fact was found |
| Review | `GET /api/review?filter=` | live; card types `fact`, `rule`, `merge` (same or newer version of a known fact) and `disagreement`, with `alternative` = the known fact; optional `warning` (the source had hidden instructions) and `outdated` |
| Review | `POST /api/review/{id} {decision: approve|reject|edit, edited_text?, reason?}` | live |
| Calendar | `GET /api/calendar?month=2026-11` | live; `connected` is false until Joey's Google sync is wired |
| Knowledge | `GET /api/knowledge?tab=&q=` | live (tabs rules, tips, contacts, sponsors; `documents` empty) |
| Knowledge | `GET /api/knowledge/{item_id}` | live |
| Handover | `GET /api/handover/{role}` | live (C-19): current approved knowledge, all citations and explicit gaps; deterministic, no model call |
| Settings | `GET /api/cabinet`, `POST /api/cabinet`, `DELETE /api/cabinet {member_id}` | live |
| Settings | `POST /api/documents` (multipart `file`) | live: .txt, .md, .csv, .eml, .xlsx up to 2 MB; past expense forms become a price list without AI; returns a `documents` knowledge item saying how many facts went to Review |
| Settings | `GET /api/usage` | live (monthly planning cost; `calls_label` identifies planner steps; optional `run_metrics`, `trace_metrics`, `trace_metrics_available`, `metrics_note` explain C-20 outcomes and recorded coverage) |
| Setup | `POST /api/setup/next` | 501 until T-20 |

The demo-only actions in `client.ts` (`/__ui/*`) stay demo-only for now.

## Usage reporting (C-20)

Planning save/finish callbacks record cumulative run metadata under
`<data-dir>/reports/<club>/runs.jsonl`, including continued runs. No prompts, questions,
answers or step text are stored there. Old monthly API totals are retained; detailed
run outcomes cover activity recorded since C-20 was added. `calls` in that legacy view
counts planner steps, so the UI uses `calls_label: "Planner steps"`.

`run_metrics` includes recorded run, successful-plan and failure counts, planner steps,
cost, and cost per successful plan (including failed spend). Without a successful plan,
the last metric is null, not zero. Recorded metrics use Asia/Beirut months. Producers
with known club context can call `clubops.reports.traces.record_trace` for metadata-only
token, latency, retry and failure metrics; reports never consume the unscoped global
trace file. No trace rows means `trace_metrics_available: false`. Trace cost and run
cost overlap and must not be added together.

```sh
python -m clubops.reports --data-dir data/app --club running-club --month 2026-10 --output results/tmp/usage.json
```

Keep real reports private. Current regression and browser runs use scripted/synthetic
activity; a real-provider pilot report remains part of C-20 validation.
