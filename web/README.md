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

## Scope

C-01 to C-12 cover the frontend against fake data. C-13 requires the backend API; C-14 requires deployment access and T-25. A local demo must never imply that anything was sent to OSA, Google or another person.
