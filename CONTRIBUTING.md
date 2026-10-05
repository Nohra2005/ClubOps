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
