# Native backlog fields and Monday weeks (C-31)

D-137 restores C-31 and supersedes D-133. Christophe reports four Monday meeting
dates: 2, 9, 16 and 23 November. [Weekly commit-history summaries](board/weekly-reviews.md)
link actual repository activity; they do not assert attendance or oral decisions.

The older additive importer populated only separate ClubOps fields. The explicit
native reconciler also populates the fields GitHub normally displays:

| Task state                     | Native Status |
| ------------------------------ | ------------- |
| todo, dependencies done        | Ready         |
| todo, dependencies outstanding | Backlog       |
| doing                          | In progress   |
| blocked                        | Blocked       |
| review                         | In review     |
| done                           | Done          |

Native Assignees map Tatiana to Nohra2005, Christophe to chrs-005 and Joey to JS9872.
The three issue cards stay on the board: #43 is assigned to Christophe, #83 to
Tatiana and #84 to Christophe. Open handoffs are In progress; closed issues map to
Done. Underlying issue state and card content are not changed.

The 26 November board also contains #128 (expiry UI, primary Christophe), #129
(fact-pipeline audit, primary Tatiana) and #169 (server turnover contract, primary
Tatiana). The reconciler accepts these explicitly known additions, uses actual
open/closed issue state and adds the primary owner without removing existing
assignees. Primary board ownership does not transfer API/web folder ownership.
The original three handoff cards remain required. Unknown, duplicate or foreign
manual issues still stop the run before mutation; no ownership is guessed from
a title or arbitrary card body (D-255/F-510).

Native Iteration uses the four Monday weeks. Open items are planned in the current
week; done tasks use their first recorded done date in main's TASKS history. Earlier
completed baseline work stays unassigned rather than being backdated. Priority,
Size and Estimate are present-day planning estimates, not historical commitments or
measured effort. The three issue handoffs emphasize active integration/deployment.
Legacy ClubOps sprint values and Wednesday plans are retained as history; native
Iteration is the current backlog grouping.

## One bulk reconciliation

```sh
cd web
npm run board:reconcile:plan
npm run board:reconcile
```

The default CLI is read-only. Applying requires both --apply and --native-fields;
meeting dates are pinned in project-native-board.json. Source defaults to the exact
origin/main TASKS.md revision, so unmerged task-status changes are not represented
as merged work. Fetch main before running. Update TASKS through reviewed PRs, then
rerun this same command to maintain status/owners as the work progresses.

One invocation refreshes the existing task mirror, preserves existing Status option
IDs while adding Blocked, creates missing Monday iterations without deleting old
IDs, assigns native values, and reads everything back. GitHub mutations use bounded
five-operation requests; this is a bulk run, not an atomic server transaction.
A partial failure is not blindly replayed. Inspect read-back and resume explicitly;
completed operations are reconciled without duplicating cards or iterations.

The apply result requires zero remaining native mutations, unchanged card content,
retained view configuration and a private board. The live receipt is stored under
output/ first; publish only its reviewed metadata projection as evidence. No real
club data, credentials or calendar-provider calls are involved.

[GitHub's Projects API](https://docs.github.com/en/graphql/reference/projects)
provides native draft assignees and project field/iteration updates. Synthetic
regressions are in scripts/project-native.test.mjs (F-249); they do not contact the
live board. No live action happens in CI.

## Verified 23 November run

[Live read-back receipt](board/evidence/native-fields-2026-11-23.json): one bulk
invocation, 93 task cards plus 3 issue cards, native assignees/status/iterations and
planning values verified; 542 native mutations and zero remaining native changes.
The source is the pinned merged TASKS revision, not unmerged completion claims.
All three issue handoffs are In progress: #43 and #84 Christophe, #83 Tatiana.
