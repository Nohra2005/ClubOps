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

The frontend defaults to a synthetic demo API until T-22 exists. Christophe chose Google sign-in for now, with an adapter that can later support university email access. Production sign-in still needs backend integration in C-13; demo role switching does not authenticate anyone.

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
```

Browser tests default to installed Google Chrome. To use Playwright's own Chromium, run `npx playwright install chromium` and set `PLAYWRIGHT_CHANNEL=bundled` before the browser tests (PowerShell: `$env:PLAYWRIGHT_CHANNEL = 'bundled'`). The tests start Vite automatically and include WCAG accessibility scans. These tests have not been added to the shared root CI workflow; its owner can run the same commands in a frontend job.

## API connection and hosting

Copy `.env.example` to `.env.local`. Change `VITE_API_MODE` to `http` to use the real transport; `VITE_API_BASE` defaults to `/api`. Vite proxies local `/api` requests to port 8000. Set `VITE_AUTH_LOGIN_URL` only after Tatiana provides the backend Google OAuth/session redirect. Never put API keys, OAuth client secrets or other secrets in `VITE_*` variables: they are public build-time configuration.

See [API_NOTES.md](API_NOTES.md) for the response and endpoint questions blocking C-13. Actions without an agreed endpoint work only in the demo and return an unavailable-action error in HTTP mode. Production chat history must be supplied by the backend; it does not use the demo cache.

For shared hosting, build with `npm ci && npm run build` in `web/`, serve `web/dist/` as static files, route `/api/*` to the backend, and rewrite other unknown routes to `index.html`. Use the same origin for authenticated cookies. `npm run preview` is a local build check, not the production server. Real Google OAuth, calendar access, forwarding email, agent calls and deployment remain backend/integration work.

## Failure-state previews

In demo mode, open a page with `?scenario=empty`, `loading`, `offline`, `ai-error`, `fallback` or `limit`. `/events/new?scenario=limit` exercises the partial-plan limit; `/chat?scenario=fallback` marks a downgraded answer after an explicit Ask click. These controls are disabled by the HTTP transport. Switch demo roles in the account menu and clubs at the top left.

## Scope

C-01 to C-12 cover the frontend against fake data. C-13 requires the backend API; C-14 requires deployment access and T-25. A local demo must never imply that anything was sent to OSA, Google or another person.
