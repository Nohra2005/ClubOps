# Task board and weekly sprints (C-31)

The tool is prepared in PR #55. **No live board has been published:** the current
GitHub CLI token lacks `read:project` / `project`, and the browser host is unavailable.
The project owner is configured as `chrs-005`. No token belongs in this repository,
CI secrets or a chat message. The GitHub connector currently exposes no Projects tools.

## Preview, publish and sync

From the repository root, with Node 22.12+ and Git installed:

```sh
git fetch origin
node web/scripts/project-board.mjs
```

This writes `output/project-board-plan.json` and makes **no network calls or remote
changes**. It reads the committed `origin/main:TASKS.md`, pins its exact commit and
hashes the input. Uncommitted task edits are not silently presented as main. Use
`--ref HEAD` only to deliberately preview a feature branch; card source links then
identify that branch's exact commit. `web/project-board.json` holds the proposed
weeks; review it before publication.

An authorized operator must enable Projects access through GitHub's own login flow:

```sh
gh auth refresh -s project
```

After authorization, the prepared publish command is:

```sh
node web/scripts/project-board.mjs --apply --create
```

It creates or reuses the dedicated private project under the authenticated owner,
links the repository, configures fields/iterations and a board view, and reconciles
the task cards. Record the returned URL and project number. Then sync after task
PRs merge using that existing number:

```sh
git fetch origin
node web/scripts/project-board.mjs --apply --project-number NUMBER
```

Only a read-back matching every managed task field produces `verified: true` in
`output/project-board-sync.json`. A partial API failure can be rerun; existing marked
cards are reused. The tool never deletes cards, changes project collaborators or
creates repository issues. The owner must separately invite Tatiana (`Nohra2005`)
and Joey (`JS9872`) to the private project so the team can see it. Keep it private.
If repository linking or owner access is refused, ask the repository/project owner;
do not create a public substitute or claim the board is complete.

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
  while authorization is missing. Its schema fields were checked by introspection.

The implementation follows GitHub's current [Projects API reference](https://docs.github.com/en/graphql/reference/projects)
and [API guide](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects).

## Weekly review evidence

| Proposed week (Asia/Beirut) | Tentative Christophe focus                                    | Actual team review |
| --------------------------- | ------------------------------------------------------------- | ------------------ |
| 2–8 November 2026           | C-21, C-27, C-29, C-31: setup, reproducibility, board         | Not held/recorded  |
| 9–15 November 2026          | C-13, C-14, C-18, C-20: integration and configured deployment | Not held/recorded  |
| 16–22 November 2026         | C-22, C-28, C-30: evaluation gates, demo, grading pointers    | Not held/recorded  |
| 23–29 November 2026         | C-15: final demo support                                      | Not held/recorded  |

These are proposed iterations, not a claim that anyone attended a meeting or
committed to a date. At each real ten-minute review, agree the week's tasks,
dependencies and carry-over; add one factual line under T-28 with date, participants,
decisions and the board/PR link. Record only what happened. Keep previous review
entries; do not backdate them. C-31 is done only when the live board matches TASKS.md
and **three actual weekly reviews** have been recorded.

The current `AGENTS.md` requires independent review and **Create a merge commit**.
That supersedes the older squash-merge line in `CONTRIBUTING.md`; its owner was asked
to reconcile the wording. No sprint, branch protection or review evidence is invented.

## Tests

```sh
cd web
npm run test:tools
npm run check
```

The stateful synthetic API tests cover 123 cards across pages, partial-write recovery,
no changes on a second sync, unsafe-target refusal, unrelated-card preservation and
iteration identity preservation. The plan validates against the real task file too.
