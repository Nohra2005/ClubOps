# Handoff log — Web app

Owner: Christophe El Chabab. Tasks in `TASKS.md`; protocol in `AGENTS.md`. See `docs/handoff/TEMPLATE.md` for the entry format. Append new entries at the bottom.

No entries yet.

## 2026-10-22 — Christophe, with Codex (feat/christophe-web-app)

**Did:** Built C-01 through C-12 from Tatiana's 14-page UI PDF: responsive React/TypeScript app, isolated persistent demo API plus guarded HTTP transport, all seven main screens, event planning/approval, Google sign-in entry, ASME setup and failure states. Google was explicitly chosen by Christophe; real OAuth still needs the backend. Work is split across small commits by feature and correction.

**State:** Frontend checks pass: 13 unit tests, 36 desktop/375px browser tests including accessibility, lint, formatting, types and production build. Existing 116 Python tests and root checks pass (UTF-8 mode for the Windows schema script). `web/VERIFICATION.md` records commands and limits. This entry is committed with the handoff; a draft PR is prepared next. Shared backend modules/contracts were not changed.

**Next:** C-13: agree the response models and missing action/auth endpoints in `web/API_NOTES.md` with Tatiana after T-22, then switch `VITE_API_MODE` from demo to http and test against the real API. C-14 waits for T-25 and C-13.

**Open questions / blockers:** Run detail-confirmation representation, revision-bound approval, action endpoints absent from the PDF, Google session/logout and calendar metadata, production chat history, shared-host SPA routing. Root CI still needs a frontend job from its owner. Synthetic fixtures and mock role switching are never production authentication or verified AUB policy.
