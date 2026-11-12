# Task board and weekly sprints (C-31)

**Live result, 12 November:** the existing private board now has **90 task drafts +
the three original manual cards (93 total)**. Source is merged main `2fff794`.
All task fields were read back and verified; the next sync created **0** cards and
made **0** updates. Metadata-only evidence: [`board/evidence/live-sync.json`](board/evidence/live-sync.json).
Original Status/Iteration fields and manual content remain intact; five separate
ClubOps fields and the **ClubOps tasks by status** view were added. No collaborator
or visibility change and no duplicate project.

**One visual step remains:** open that view, choose **Group by → ClubOps status**,
then save. Read-only API inspection confirms view #7 is a board with no grouping
yet. Browser control stopped because it could not verify Chrome's URL, so no visual
completion is claimed. The API cannot set grouping through its supported view input.
C-31 remains doing until this step and **three actual weekly team reviews** are evidenced.
GitHub automatically categorizing a past iteration as completed is not a team review.
Statuses in unmerged PRs are not published; merge them, then sync main again.

Tatiana reports in #43 that she already created **ClubOps** in the repository's
Projects tab and gave Christophe admin access. Use that existing board; do not
create a second project. The prepared config now targets `Nohra2005` / `ClubOps`
and Wednesday-start weeks from 4 November. The owner/number, private visibility,
fields and three existing cards were read back on 12 November. Iteration dates/IDs,
were inspected before adoption; read access alone did not prove sync.

Christophe supplied the exact existing board URL on 11 November:
**https://github.com/users/Nohra2005/projects/4** (owner `Nohra2005`, number `4`).
This is the existing target; it was adopted in place, not recreated.

**Pre-adoption audit, 12 November:** access works for `chrs-005`. Project #4 is
**ClubOps**, owned by `Nohra2005`, private and open. Read-back returns 17 fields and
three repository issue cards: #43 (coordination), #83 (Tatiana handoff),
#84 (Christophe handoff). All three are in Backlog; they are manual issue cards,
not managed task drafts. At that inspection no remote state had been changed.

Status uses **Backlog, Ready, In progress, In review, Done**. There is an
**Iteration** field, not the importer's **Sprint**, and the README has no management
marker. These differ from the dedicated importer’s canonical task statuses and
fields. Normal `--apply` refused this unmarked layout: do not overwrite the README,
reset options/iteration IDs, relabel existing cards or create a duplicate board.
An explicit additive adapter is now implemented with synthetic refusal/retry tests
and complete before/after read-back. Its read-only preview identified
90 tasks and three manual cards; preview alone published nothing. The original
Iteration has no active or completed entries. Preserve all three issue cards and
manual history. Three
actual weekly reviews remain unrecorded; planned dates are not completed reviews.

**Historical check, 11 November (resolved):** GitHub CLI authenticates as `chrs-005`; the token's
OAuth scopes include `project`. `gh project view 4`, `field-list 4` and `item-list 4`
all return `Could not resolve to a ProjectV2 with the number 4`. Browser app access
timed out, so no board contents were inferred from the UI. This error does not
distinguish missing permission from a missing board.
The 12 November read-back above supersedes that access blocker.
No board fields, cards, visibility or collaborators have been changed, and no
second project has been created. The request is in coordination issue #43.

Projects authorization was already enabled; do not keep repeating the OAuth flow
for this account. No token belongs in this repository, CI secrets or a chat message.

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

For a **new operator** who lacks Projects scope, use GitHub's authorization flow
(include `project` after `-s`). The current operator already has it:

```sh
gh auth refresh -s project
gh project list --owner Nohra2005 --format json
```

Re-inspect the supplied existing target before adoption:

```sh
gh project view 4 --owner Nohra2005 --format json
gh project field-list 4 --owner Nohra2005 --limit 100 --format json
gh project item-list 4 --owner Nohra2005 --limit 100 --format json
```

Those CLI lists are a first inspection; a 100-item list is not proof that a larger
board was fully read. The sync adapter paginates all cards. Verify the returned owner,
URL, private/open status, access, existing task identities, fields and sprint dates.
Reconcile the local config to actual iterations while preserving existing IDs.

**Explicit adoption:** normal sync still rejects an unmarked board. Inspect an
existing target without writes first:

```sh
node web/scripts/project-board.mjs --adopt --project-number 4 --out output/adoption-preview.json
```

This checks exact owner/number/title, private/open/write access, every item page,
duplicate task identities, reserved namespace collisions and incompatible views.
Only an explicit `--apply` can append a project/repository-bound marker to the
existing README and create the separate managed fields/view:

```sh
node web/scripts/project-board.mjs --adopt --apply --project-number 4
```

The five new fields are **ClubOps status**, **ClubOps owner**, **ClubOps task id**,
**ClubOps needs**, **ClubOps sprint**. Existing Status, Iteration, views and manual
cards stay intact. Existing README text remains an exact prefix. If a reserved name
already exists on an unmarked board, adoption refuses rather than claiming it.
Partial field/card writes resume via normal sync without a second marker or duplicate.

In the new **ClubOps tasks by status** view, select **Group by → ClubOps status** in
GitHub and save the view. The API’s view configuration only supports visible fields,
so the receipt explicitly requires this UI verification. Optionally filter the view
to task cards using the UI; the three original manual cards have no ClubOps status.
Do not change their original Status or claim an API card check proves visual grouping.

After the existing board is safely reconciled with the importer, sync merged task PRs:

```sh
git fetch origin
node web/scripts/project-board.mjs --apply --project-number 4
```

Only matching read-back produces `verified: true` in `output/project-board-sync.json`.
Partial failure is retryable; existing marked cards are reused. The tool does not delete
cards, change collaborators or create repository issues. Tatiana reports Christophe
is admin; current viewerCanUpdate is true, while Joey's visibility still needs verification. Keep it private.
`--create` remains available for new dedicated projects, but is not this project's
next action and refuses a different authenticated owner.

## Source of truth and limits

- One draft card per active task in `TASKS.md`; dropped commented-out tasks are omitted.
- ClubOps status values exactly match `todo`, `doing`, `blocked`, `review`, `done`;
  the visual columns require the grouping step above.
- The adopted board uses the ClubOps-prefixed fields above. Dedicated boards retain
  the original Status/Owner/Task ID/Needs/Sprint names.
- Edit task status in `TASKS.md` through the reviewed PR workflow, then sync; don't
  independently maintain a contradictory status in Projects. Owners are task roles,
  not unapproved assignments to teammates' accounts.
- Source links point to the evaluated commit. Sprint assignments come from the
  committed plan, remain tentative and do not waive task dependencies or hosting costs.
- Use one sync operator at a time. Crash/retry idempotence is tested; simultaneous
  writers from separate machines have no distributed lease. Duplicate identities
  cause a safe refusal and require reconciliation, not automatic deletion.
- Only a dedicated or explicitly adopted managed project is accepted. Public/closed/unmanaged projects,
  conflicting field types/options, duplicate task identities and changed sprint dates
  are rejected. Historical iteration IDs are preserved when new weeks are appended.
- Projects access is needed only by the operator; CI runs synthetic API doubles with
  no token or network writes. Live write/read-back and repeat-sync no-op are now
  verified on the actual board; supported schema fields were checked by introspection.
  Normal unmarked-board refusal remains intentional.

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

The 25 synthetic tool tests cover 123 tasks plus three manual cards across
pages, interrupted field/card creation, repeat-sync no-ops, unsafe-target refusal,
manual content/field/view preservation, read-back tampering and cyclic pagination.
The plan validates against the real task file too. Error tests keep raw diagnostics
out of output. They make no GitHub writes. The live request size is bounded at five
mutations: the earlier larger batches stopped after partial creations. Read-back
recovered 29 existing task drafts; the completed attempt created the remaining 61
and applied 372 field updates. A second sync verified zero changes.
