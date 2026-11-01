# ClubOps frontend

Christophe's frontend, based on Tatiana's UI specification dated 22 October 2026. React + TypeScript + Vite. The backend and frozen Python contracts are owned by Tatiana and are not modified here.

## Development

Requires Node 22.12+ (Node 24 also works).

```sh
cd web
npm ci
npm run dev
```

Open the local URL printed by Vite. `npm run build` type-checks and builds a static application in `web/dist/`. A production host must rewrite application routes such as `/events/ev-example` to `index.html`, while routing `/api/*` to the backend.

The frontend defaults to a synthetic demo API. T-22 part 1 is available; set HTTP mode to connect it. Google sign-in now uses the published credential/session exchange. A real OAuth client ID and deployed verification are still pending; demo role switching does not authenticate anyone.

## What is ready

C-01 through C-12 are implemented against the demo API:

- Responsive workspace, shareable routes, role-aware controls and Google sign-in entry point.
- Event overview, intake/confirmation, bounded agent run panel, questions, revisions, six event tabs, explicit plan approval and after-event review.
- Sourced chat, uncertainty, disagreement, teaching, feedback and per-user demo history.
- Grouped review, safe fact batches, rule confirmation state and source comparisons.
- Month calendar, role filters, task completion and connection status.
- Five knowledge categories, search, source excerpts, edit proposals and retirement.
- Role guides, gaps, text export, browser print/PDF and explicit handover sign-off.
- Cabinet/settings, document upload, email paste, usage report and skippable ASME setup.
- Loading, empty, error, offline, fallback and run-limit states. No model is called by this demo.

Every fixture is synthetic. Fictional policies are marked as examples, and private Running Club fixtures are never used as ASME knowledge. Demo data is stored under `clubops.*` browser-storage keys. If storage is blocked, changes remain in the current tab and a notice explains the limitation.

## Checks

```sh
npm run check       # lint, formatting, unit tests, strict types, production build
npm run test:e2e    # real Chrome, desktop and 375px phone workflows
npm run test:e2e:http # HTTP adapter against intercepted contract responses, same two widths
npm run test:e2e:live # real local API + SQLite + scripted model (requires root uv setup)
npm run test:e2e:compose # already-running local Docker app, sign-in and routing
```

Browser tests default to installed Google Chrome. To use Playwright's own Chromium, run `npx playwright install chromium` and set `PLAYWRIGHT_CHANNEL=bundled` before the browser tests (PowerShell: `$env:PLAYWRIGHT_CHANNEL = 'bundled'`). The tests start Vite automatically and include WCAG accessibility scans. PR #44 runs these checks in the dedicated Web workflow. The existing Python workflow stays separate.

The HTTP suite starts an isolated Vite instance on port 5174 with `VITE_API_MODE=http`; responses are intercepted and synthetic. It covers runs/questions/limits, Google exchange and logout failures, usage coverage, answers, calendar items and draft rejection/retry. The live suite uses ports 8001/5175, a fresh temporary store under root `output/`, a dev-only synthetic account and a scripted planner. It verifies cookie sessions, planning, explicit approval, calendar items, handover, usage and logout without interception or model charges. Neither suite verifies a real Google account or provider. Both leave the demo preview on port 5173 running.

## API connection and hosting

Copy `.env.example` to `.env.local`. Set `VITE_API_MODE=http`; `VITE_API_BASE` defaults to `/api`. Vite proxies local requests to port 8000 (override with server-only `CLUBOPS_API_PROXY`). Set public `VITE_GOOGLE_CLIENT_ID` to match the backend's `CLUBOPS_GOOGLE_CLIENT_ID`. Never put API keys, OAuth client secrets or other secrets in `VITE_*`: they are public build-time configuration. See [the published API](../docs/api.md) for backend startup and cabinet setup.

See [API_NOTES.md](API_NOTES.md) for current integration coverage and remaining server features. Actions without an agreed endpoint work only in the demo and return an unavailable-action error in HTTP mode. Production chat history must be supplied by the backend; it does not use the demo cache.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the verified local Docker/Caddy image, Compose setup, persistent Render configuration and Google setup. From the root, `docker compose up --build` serves the real API at `http://127.0.0.1:8080/login` with an explicit synthetic local sign-in. Data and the generated local signing key survive container replacement. No public service or paid resource has been created. Hosting needs an account-owner decision. `npm run preview` is a local build check, not the production server.

PR #44 adds real frontend and container gates in `.github/workflows/web.yml` and `container.yml`; see [ENGINEERING_EVIDENCE.md](ENGINEERING_EVIDENCE.md) for run links and remaining bonus tasks. The shared Python workflow is unchanged. Frontend/browser failure artifacts contain synthetic test activity only.

## Failure-state previews

In demo mode, open a page with `?scenario=empty`, `loading`, `offline`, `ai-error`, `fallback` or `limit`. `/events/new?scenario=limit` exercises the partial-plan limit; `/chat?scenario=fallback` marks a downgraded answer after an explicit Ask click. These controls are disabled by the HTTP transport. Switch demo roles in the account menu and clubs at the top left.

## Scope

C-01 to C-12 cover the frontend against fake data. C-13 is integrated with the available API; unfinished server capabilities and deployed Google verification remain pending. C-14 depends on C-13 and C-18. A local demo must never imply that anything was sent to OSA, Google or another person.
