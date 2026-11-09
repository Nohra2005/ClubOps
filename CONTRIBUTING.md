# Contributing

## Workflow

1. Every piece of work is a task in [`TASKS.md`](TASKS.md), with an owner. Read [`AGENTS.md`](AGENTS.md) for the team protocol.
2. Branch from `main`: `feat/<area>-<short-name>`, `fix/…`, `eval/…`, `docs/…`.
3. Open a pull request early. Fill in the template.
4. **One approving review from a teammate** and a green CI before merging. Merge: **Squash and merge** for your own PR; **Create a merge commit** for a teammate's PR, so their commits keep their name (AGENTS.md rule 10).
5. Nobody pushes to `main` directly. Branch protection isn't available on a free private repo (GitHub returns 403), so this is by agreement.

## Contract changes

Contracts are the agreements between our parts; changing one can silently break a teammate's work.

- A PR that changes anything in `src/clubops/contracts/` or the registry is labelled `contract-change`.
- Bump the version (`SCHEMA_VERSION` and the capability's version), run `make schemas`, update tests.
- The contracts owner (CODEOWNERS) must approve it.
- Provisional capabilities may change freely until their phase starts.

## Definition of done

- `make check` passes: lint, strict types, tests with ≥ 85% coverage, generated schemas up to date.
- New behaviour has tests, including at least one failure case.
- Every new failure mode has a Failure Matrix row and a regression test.
- Docs that point at the change (`rubric-map.md`, `evidence.md`, `capabilities.md`) are current.

## Data rules

- Real club data (chat exports, emails, interview notes) **never** goes in git. Keep it in `data/raw/`, which is ignored.
- Fixtures and tests use synthetic data only.
- Secrets live in `.env` (ignored). Copy `.env.example`.

## Ownership

Decided 2026-10-22 (design log D-46). Folders and contracts per owner are in [`AGENTS.md`](AGENTS.md).

| Area | Owner | Handoff log |
|---|---|---|
| Backend, agent, memory, evaluation | Tatiana Nohra | `docs/handoff/capture-and-evaluation.md`, `docs/handoff/contracts-knowledge-handover.md`, `docs/handoff/event-packet.md` |
| Web app | Christophe El Chabab | `docs/handoff/web.md` |
| Calendar, reminders, draft templates | Joey Saade | `docs/handoff/calendar-and-drafts.md` |

Work is split by area so three people and three AI tools can work in parallel, each against the contracts. Cross-area changes go through a PR the other owner reviews.

## Session handoff

Area ownership doesn't solve continuity *within* an area — work on one area still gets picked up across multiple sessions, sometimes by a different AI tool than last time, sometimes after a few days away. For that, each area keeps a running handoff log in `docs/handoff/<area>.md`.

- Before ending a work session on an area (finished the task or not), append an entry to that area's log: what you did, whether it's committed/pushed/in review, the one most useful next step, and any open question or assumption you made that should be checked. Use `docs/handoff/TEMPLATE.md`'s field list.
- Starting a session on an area: read that area's log (just the last couple of entries, not the whole history) before starting, the same way `find-gaps`/`plan-interview` read the club's own know-how log before an officer handover — this project eats its own dog food here on purpose.
- The log is additive — append at the bottom, don't rewrite old entries. It's a record of what actually happened, not a status board; `TASKS.md` is the status board.
- A log entry is not a substitute for a commit message, a PR description, or Failure Matrix rows — it's the "what would I tell the next person in five sentences" layer that those don't cover.
