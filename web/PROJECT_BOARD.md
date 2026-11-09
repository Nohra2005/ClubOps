# Task board and weekly sprints (C-31)

Tatiana reports in #43 that she already created **ClubOps** in the repository's
Projects tab and gave Christophe admin access. Use that existing board; do not
create a second project. The prepared config now targets `Nohra2005` / `ClubOps`
and Wednesday-start weeks from 4 November. The owner/number, private visibility,
existing fields/cards and iteration IDs still need live read-back after authorization.
Her report is not a claim that this CLI has verified or synced the board.

Projects authorization was enabled on 9 November for `chrs-005`. Read-only discovery
then returned no visible boards under `Nohra2005`, `chrs-005` or the repository
(all connections fully read). The direct board URL/access must be confirmed with
Tatiana before live sync; a repository URL does not identify a project. No token belongs in this repository, CI
secrets or a chat message. The GitHub connector exposes no Projects tools here.

## Preview and inspect the existing board

From the repository root, with Node 22.12+ and Git installed:

```sh
git fetch origin
node web/scripts/project-board.mjs
```

This writes `output/project-board-plan.json` without network calls or remote changes.
It reads committed `origin/main:TASKS.md`, pins the exact commit and hashes the input.
Use `--ref HEAD` only for a deliberate feature-branch preview. The current-main dry
run on 9 November reads 85 tasks; it does not publish this branch's task-status edits.
Sprint task assignments/titles remain proposals until reconciled with the live board.

Enable Projects through GitHub's own authorization flow (include `project` after `-s`):

```sh
gh auth refresh -s project
gh project list --owner Nohra2005 --format json
```

Identify the existing ClubOps project number and inspect it first:

```sh
gh project view NUMBER --owner Nohra2005 --format json
gh project field-list NUMBER --owner Nohra2005 --limit 100 --format json
gh project item-list NUMBER --owner Nohra2005 --limit 100 --format json
```

Those CLI lists are a first inspection; a 100-item list is not proof that a larger
board was fully read. The sync adapter paginates all cards. Verify the returned owner,
URL, private/open status, access, existing task identities, fields and sprint dates.
Reconcile the local config to actual iterations while preserving existing IDs.

**Current importer limit:** normal sync requires the dedicated management marker and
rejects unmarked task cards or incompatible status fields. A manually created board
may need an additive adoption adapter after inspection. Do not stamp a marker over
unreviewed content, replace a README, reset live fields, delete cards, change visibility
or create a duplicate board to bypass a refusal. Inspect and adapt the importer first;
record the actual board URL and read-back evidence when that work is complete.

After the existing board is safely reconciled with the importer, sync merged task PRs:

```sh
git fetch origin
node web/scripts/project-board.mjs --apply --project-number NUMBER
```

Only matching read-back produces `verified: true` in `output/project-board-sync.json`.
Partial failure is retryable; existing marked cards are reused. The tool does not delete
cards, change collaborators or create repository issues. Tatiana reports Christophe
is admin; live access and Joey's visibility still need verification. Keep it private.
`--create` remains available for new dedicated projects, but is not this project's
next action and refuses a different authenticated owner.

## Source of truth and limits

- One draft card per active task in `TASKS.md`; dropped commented-out tasks are omitted.
- Status columns exactly match `todo`, `doing`, `blocked`, `review`, `done`.
- Custom Owner, Task ID, Needs and Sprint fields make responsibility and blockers visible.
- Edit task status in `TASKS.md` through the reviewed PR workflow, then sync; don't
  independently maintain a contradictory status in Projects. Owners are task roles,
  not unapproved assignments to teammates' accounts.
- Source links point to the evaluated commit. Sprint assignments come from the
  committed plan, remain tentative and do not waive task dependencies or hosting costs.
- Use one sync operator at a time. Crash/retry idempotence is tested; simultaneous
  writers from separate machines have no distributed lease. Duplicate identities
  cause a safe refusal and require reconciliation, not automatic deletion.
- Only the dedicated managed project is accepted. Public/closed/unmanaged projects,
  conflicting field types/options, duplicate task identities and changed sprint dates
  are rejected. Historical iteration IDs are preserved when new weeks are appended.
- Projects access is needed only by the operator; CI runs synthetic API doubles with
  no token or network writes. The live adapter has not been exercised against a board
  while the existing board is not visible to this account. Its schema fields were
  checked by introspection.

The implementation follows GitHub's current [Projects API reference](https://docs.github.com/en/graphql/reference/projects)
and [API guide](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects).

## Weekly review evidence

| Proposed week (Asia/Beirut) | Tentative Christophe focus                                    | Actual team review        |
| --------------------------- | ------------------------------------------------------------- | ------------------------- |
| 4–10 November 2026          | C-21, C-27, C-29, C-31: setup, reproducibility, board         | No evidence recorded here |
| 11–17 November 2026         | C-13, C-14, C-18, C-20: integration and configured deployment | No evidence recorded here |
| 18–24 November 2026         | C-22, C-28, C-30: evaluation gates, demo, grading pointers    | No evidence recorded here |
| 25 November–1 December 2026 | C-15: final demo support                                      | No evidence recorded here |

Tatiana confirmed Wednesday reviews after office hours in #43. The sprint cadence
is agreed; task allocations remain tentative. No meeting attendance or completed
review is claimed here. The last seven-day iteration crosses the 30 November
submission deadline; all final handoff work must finish by that deadline. At each real ten-minute review, agree the week's tasks,
dependencies and carry-over; add one factual line under T-28 with date, participants,
decisions and the board/PR link. Record only what happened. Keep previous review
entries; do not backdate them. C-31 is done only when the live board matches TASKS.md
and **three actual weekly reviews** have been recorded.

The current `AGENTS.md` requires independent review and **Create a merge commit**.
`CONTRIBUTING.md` now agrees after main PR #59. No sprint, branch protection or review evidence is invented.

## Tests

```sh
cd web
npm run test:tools
npm run check
```

The stateful synthetic API tests cover 123 cards across pages, partial-write recovery,
no changes on a second sync, unsafe-target refusal, unrelated-card preservation and
iteration identity preservation. The plan validates against the real task file too.
