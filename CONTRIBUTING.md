# Contributing

## Workflow

1. Every piece of work starts as an issue on the GitHub Projects board, with an owner and a phase.
2. Branch from `main`: `feat/<area>-<short-name>`, `fix/…`, `eval/…`, `docs/…`.
3. Open a pull request early. Fill in the template.
4. **One approving review from a teammate** and a green CI are required to merge. Squash-merge.
5. Nobody pushes to `main` directly (branch protection).

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

## Ownership (proposal, to be confirmed by the team)

| Area | Owner |
|---|---|
| Contracts, knowledge base, handover | Tatiana Nohra |
| Capture from chats and emails, evaluation datasets | Christophe El Chabab |
| Event packet: intake, rules, proposal, approval queue UI | Joey Saade |

Everyone reviews outside their own area at least once a week.

This is the primary way work is split: by area, not by who happens to be free. The contracts are frozen interfaces between areas specifically so three people (and three different AI tools) can work inside their own area in parallel without stepping on each other — that's the whole point of ADR 0001. Pick up your next task from the area you own; cross-area work goes through a PR the other owner reviews.

## Session handoff

Area ownership doesn't solve continuity *within* an area — work on one area still gets picked up across multiple sessions, sometimes by a different AI tool than last time, sometimes after a few days away. For that, each area keeps a running handoff log in `docs/handoff/<area>.md`.

- Before ending a work session on an area (finished the task or not), append an entry to that area's log: what you did, whether it's committed/pushed/in review, the one most useful next step, and any open question or assumption you made that should be checked. Use `docs/handoff/TEMPLATE.md`'s field list.
- Starting a session on an area: read that area's log (just the last couple of entries, not the whole history) before starting, the same way `find-gaps`/`plan-interview` read the club's own know-how log before an officer handover — this project eats its own dog food here on purpose.
- The log is additive — append at the bottom, don't rewrite old entries. It's a record of what actually happened, not a status board; GitHub Issues and the Projects board are the status board.
- A log entry is not a substitute for a commit message, a PR description, or Failure Matrix rows — it's the "what would I tell the next person in five sentences" layer that those don't cover.
