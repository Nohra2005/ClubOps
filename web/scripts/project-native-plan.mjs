/** Pure native-board planning and configuration; never mutates GitHub. */
import { operation, preflight } from './project-github.mjs';

export const ownerLogins = { tatiana: 'Nohra2005', christophe: 'chrs-005', joey: 'JS9872' };
// Explicit primary backlog owners; issue assignments already present are retained.
const issueOwners = {
  43: 'christophe',
  83: 'tatiana',
  84: 'christophe',
  128: 'christophe',
  129: 'tatiana',
  169: 'tatiana',
};
const requiredIssues = [43, 83, 84];
const critical = new Set([
  'T-06',
  'T-26',
  'T-27',
  'T-32',
  'T-44',
  'T-46',
  'T-47',
  'C-13',
  'C-14',
  'C-18',
  'C-21',
  'C-22',
  'C-29',
  'J-20',
]);
export const nativeNote = '<!-- clubops-native-fields:v1 -->';
export const nativeDescription = `${nativeNote}\nNative Status, Assignees, Iteration, Priority, Size and Estimate are reconciled by project-native-board.mjs with the owner's authorization. This supersedes the earlier manual-field note for those fields only. Task statuses come from the pinned TASKS.md commit. Monday meeting dates were reported by Christophe; iteration allocations and point estimates are present-day planning/grouping, not original meeting commitments. Historical topics are linked commit-history summaries, not verified minutes.\n<!-- /clubops-native-fields:v1 -->`;

export function mondayWeeks(dates) {
  if (!Array.isArray(dates) || dates.length !== 4)
    throw new Error('Supply the four confirmed Monday dates');
  const weeks = dates.map((startDate, index) => {
    const time = Date.parse(`${startDate}T00:00:00Z`);
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(startDate) ||
      !Number.isFinite(time) ||
      new Date(time).toISOString().slice(0, 10) !== startDate ||
      new Date(time).getUTCDay() !== 1 ||
      (index && time - Date.parse(`${dates[index - 1]}T00:00:00Z`) !== 7 * 86400000)
    )
      throw new Error('Meeting weeks must be four consecutive Mondays');
    return { title: `Sprint ${index + 1}: week of ${startDate}`, startDate, duration: 7 };
  });
  return weeks;
}

export function field(project, name, type) {
  const matches = project.fields.nodes.filter((x) => x.name === name);
  if (matches.length !== 1 || matches[0].dataType !== type)
    throw new Error(`Native ${name} field missing or ambiguous`);
  return matches[0];
}
export const iterations = (f) => [
  ...f.configuration.completedIterations,
  ...f.configuration.iterations,
];

export function configurationChanges(project, dates) {
  const weeks = mondayWeeks(dates);
  const status = field(project, 'Status', 'SINGLE_SELECT');
  for (const name of ['Backlog', 'Ready', 'In progress', 'In review', 'Done'])
    if (!status.options.some((x) => x.name === name))
      throw new Error('Unrecognized native status configuration');
  const operations = [];
  if (!status.options.some((x) => x.name === 'Blocked'))
    operations.push(
      operation(
        'updateProjectV2Field',
        'UpdateProjectV2FieldInput',
        {
          fieldId: status.id,
          singleSelectOptions: [
            ...status.options,
            { name: 'Blocked', color: 'RED', description: 'Blocked in TASKS.md' },
          ],
        },
        'projectV2Field { ...on ProjectV2SingleSelectField { id options { id name } } }',
      ),
    );
  const sprint = field(project, 'Iteration', 'ITERATION');
  const existing = iterations(sprint);
  const missing = weeks.filter(
    (w) => !existing.some((x) => x.startDate === w.startDate && x.duration === 7),
  );
  if (existing.some((x, i) => existing.slice(i + 1).some((y) => x.startDate === y.startDate)))
    throw new Error('Duplicate native iteration dates');
  for (const w of weeks)
    for (const x of existing) {
      const start = Date.parse(w.startDate),
        other = Date.parse(x.startDate);
      if (
        start < other + x.duration * 86400000 &&
        other < start + 7 * 86400000 &&
        !(x.startDate === w.startDate && x.duration === 7)
      )
        throw new Error('Native iteration overlap; preserving existing dates');
    }
  if (missing.length) {
    const all = [...existing, ...missing].sort((a, b) => a.startDate.localeCompare(b.startDate));
    operations.push(
      operation(
        'updateProjectV2Field',
        'UpdateProjectV2FieldInput',
        {
          fieldId: sprint.id,
          iterationConfiguration: { startDate: all[0].startDate, duration: 7, iterations: all },
        },
        'projectV2Field { ...on ProjectV2IterationField { id } }',
      ),
    );
  }
  return operations;
}

export function planNative(project, plan, dates, completedDates, { allowMissing = false } = {}) {
  if (project.url !== 'https://github.com/users/Nohra2005/projects/4')
    throw new Error('Wrong native board target');
  const managed = preflight(project, plan);
  const weeks = mondayWeeks(dates);
  configurationChanges(project, dates);
  for (const [name, type] of [
    ['Assignees', 'ASSIGNEES'],
    ['Priority', 'SINGLE_SELECT'],
    ['Size', 'SINGLE_SELECT'],
    ['Estimate', 'NUMBER'],
  ])
    field(project, name, type);
  for (const [owner, login] of Object.entries(ownerLogins))
    if (project.users?.[owner]?.login !== login || !project.users[owner].id)
      throw new Error('Owner login identity is unresolved');
  const byId = new Map(plan.cards.map((x) => [x.id, x]));
  const rows = plan.cards.map((card) => {
    if (!project.users[card.owner]) throw new Error('Unknown task owner');
    const item = managed.get(card.id);
    if (!item && !allowMissing)
      throw new Error('Task mirror must be reconciled before native writes');
    const ready = card.needs.every((id) => byId.get(id)?.status === 'done');
    const status =
      card.status === 'todo'
        ? ready
          ? 'Ready'
          : 'Backlog'
        : { doing: 'In progress', blocked: 'Blocked', review: 'In review', done: 'Done' }[
            card.status
          ];
    if (!status) throw new Error('Unknown task status');
    const priority =
      card.status === 'done'
        ? 'P2'
        : critical.has(card.id)
          ? 'P0'
          : ['doing', 'review'].includes(card.status)
            ? 'P1'
            : 'P2';
    const size = /deploy|agent|planner|chatbot|evaluation|calendar.*sync|monitor/i.test(card.title)
      ? 'L'
      : /docs|report|script|board|review|poster|handoff|grader|rules|check/i.test(card.title)
        ? 'M'
        : 'S';
    const completion = completedDates[card.id];
    const week =
      card.status === 'done'
        ? weeks.find(
            (w) =>
              completion >= w.startDate &&
              completion <
                new Date(Date.parse(w.startDate) + 7 * 86400000).toISOString().slice(0, 10),
          )
        : weeks.at(-1);
    return {
      task_id: card.id,
      item_id: item?.id,
      content_id: item?.content.id,
      kind: 'task',
      owner: card.owner,
      status,
      task_status: card.status,
      priority,
      size,
      estimate: { S: 2, M: 3, L: 5 }[size],
      iteration_start: week?.startDate ?? null,
      allocation_basis:
        card.status === 'done'
          ? week
            ? 'first_done_in_main_TASKS_history'
            : 'completed_before_requested_weeks_or_date_unavailable'
          : 'current_planning',
      assignee_id: project.users[card.owner].id,
    };
  });
  const managedIds = new Set([...managed.values()].map((item) => item.id));
  const issues = project.items.filter((item) => !managedIds.has(item.id));
  const issueNumbers = new Set(issues.map((item) => item.content?.number));
  if (
    requiredIssues.some((number) => !issueNumbers.has(number)) ||
    issueNumbers.size !== issues.length ||
    issues.some(
      (x) =>
        x.content.__typename !== 'Issue' ||
        x.content.repository?.nameWithOwner !== plan.repository ||
        !issueOwners[x.content.number],
    )
  )
    throw new Error('Unexpected manual card; explicit ownership required');
  for (const item of issues) {
    const owner = issueOwners[item.content.number];
    rows.push({
      issue: item.content.number,
      item_id: item.id,
      content_id: item.content.id,
      kind: 'issue',
      owner,
      status: item.content.state === 'CLOSED' ? 'Done' : 'In progress',
      task_status: item.content.state === 'CLOSED' ? 'done' : 'doing',
      priority: item.content.number === 43 ? 'P1' : 'P0',
      size: item.content.number === 43 ? 'S' : 'L',
      estimate: item.content.number === 43 ? 2 : 5,
      iteration_start: weeks.at(-1).startDate,
      allocation_basis: 'current_planning',
      assignee_id: project.users[owner].id,
    });
  }
  for (const row of rows)
    for (const name of ['Priority', 'Size'])
      if (
        !field(project, name, 'SINGLE_SELECT').options.some(
          (x) => x.name === row[name.toLowerCase()],
        )
      )
        throw new Error(`Missing ${name} option`);
  return rows;
}
