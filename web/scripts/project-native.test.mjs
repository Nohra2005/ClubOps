import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { URL } from 'node:url';
import { adoptionBlock } from './project-profile.mjs';
import { marker } from './project-plan.mjs';
import {
  configurationChanges,
  mondayWeeks,
  nativeOperations,
  ownerLogins,
  planNative,
  applyNative,
} from './project-native.mjs';
import { firstDone, options } from './project-native-board.mjs';

const dates = ['2026-11-02', '2026-11-09', '2026-11-16', '2026-11-23'];
const field = (name, dataType, options) => ({
  id: 'field-' + name,
  name,
  dataType,
  ...(options
    ? {
        options: options.map((name) => ({
          id: 'option-' + name,
          name,
          color: 'GRAY',
          description: name,
        })),
      }
    : {}),
});
function fixture() {
  const cards = Array.from({ length: 7 }, (_, i) => ({
    id: `C-0${i + 1}`,
    title: 'Synthetic task',
    body: 'Synthetic project data',
    owner: 'christophe',
    status: ['todo', 'todo', 'doing', 'blocked', 'review', 'done', 'done'][i],
    needs: i === 1 ? ['C-03'] : [],
  }));
  const plan = { owner: 'Nohra2005', repository: 'Nohra2005/ClubOps', cards };
  const project = {
    id: 'project-synthetic',
    url: 'https://github.com/users/Nohra2005/projects/4',
    public: false,
    closed: false,
    viewerCanUpdate: true,
    views: { nodes: [{ id: 'view-synthetic' }] },
    fields: {
      nodes: [
        field('Status', 'SINGLE_SELECT', ['Backlog', 'Ready', 'In progress', 'In review', 'Done']),
        field('Assignees', 'ASSIGNEES'),
        field('Priority', 'SINGLE_SELECT', ['P0', 'P1', 'P2']),
        field('Size', 'SINGLE_SELECT', ['S', 'M', 'L']),
        field('Estimate', 'NUMBER'),
        {
          ...field('Iteration', 'ITERATION'),
          configuration: { iterations: [], completedIterations: [] },
        },
        field('ClubOps status', 'SINGLE_SELECT', ['todo', 'doing', 'blocked', 'review', 'done']),
        field('ClubOps owner', 'SINGLE_SELECT', ['tatiana', 'christophe', 'joey']),
      ],
    },
    users: Object.fromEntries(
      Object.entries(ownerLogins).map(([owner, login]) => [owner, { id: 'user-' + owner, login }]),
    ),
  };
  project.readme = adoptionBlock(project, plan);
  project.items = cards.map((card) => ({
    id: 'item-' + card.id,
    isArchived: false,
    content: {
      __typename: 'DraftIssue',
      id: 'draft-' + card.id,
      title: card.title,
      body: `${marker}\nTask: ${card.id}\n\nSynthetic task`,
      assignees: { nodes: [] },
    },
    fieldValues: { nodes: [], pageInfo: { hasNextPage: false } },
  }));
  for (const number of [43, 83, 84])
    project.items.push({
      id: 'issue-item-' + number,
      content: {
        __typename: 'Issue',
        id: 'issue-' + number,
        number,
        state: 'OPEN',
        title: 'Synthetic issue',
        body: 'Synthetic coordination',
        repository: { nameWithOwner: plan.repository },
        assignees: { nodes: [] },
      },
      fieldValues: { nodes: [], pageInfo: { hasNextPage: false } },
    });
  return { project, plan };
}
function configure(project) {
  project.fields.nodes
    .find((f) => f.name === 'Status')
    .options.push({ id: 'blocked-option', name: 'Blocked', color: 'RED', description: 'Blocked' });
  project.fields.nodes.find((f) => f.name === 'Iteration').configuration.iterations = mondayWeeks(
    dates,
  ).map((w, i) => ({ ...w, id: 'week-' + i }));
}
function emulate(project, ops) {
  for (const op of ops) {
    const input = op.input;
    if (op.name === 'updateProjectV2') {
      project.readme = input.readme;
      continue;
    }
    if (op.name === 'updateProjectV2DraftIssue' || op.name === 'addAssigneesToAssignable') {
      const item = project.items.find(
        (x) => x.content.id === (input.draftIssueId ?? input.assignableId),
      );
      item.content.assignees.nodes = input.assigneeIds.map((id) => ({ id }));
      continue;
    }
    const item = project.items.find((x) => x.id === input.itemId);
    item.fieldValues.nodes = item.fieldValues.nodes.filter((x) => x.field.id !== input.fieldId);
    if (input.value)
      item.fieldValues.nodes.push({
        field: { id: input.fieldId },
        ...(input.value.singleSelectOptionId
          ? { optionId: input.value.singleSelectOptionId }
          : input.value.iterationId
            ? { iterationId: input.value.iterationId }
            : { number: input.value.number }),
      });
  }
}

test('four consecutive confirmed Mondays validate; invalid, duplicate and gapped dates refuse', () => {
  assert.equal(mondayWeeks(dates).length, 4);
  for (const bad of [
    [...dates.slice(0, 3)],
    ['2026-11-03', ...dates.slice(1)],
    [dates[0], dates[0], ...dates.slice(2)],
    [...dates.slice(0, 3), '2026-11-30'],
  ])
    assert.throws(() => mondayWeeks(bad));
});
test('native mapping keeps blocked distinct, derives readiness from Needs, and allocates recorded completion dates', () => {
  const { project, plan } = fixture();
  const rows = planNative(project, plan, dates, { 'C-06': '2026-11-12', 'C-07': '2026-10-30' });
  assert.deepEqual(
    rows.slice(0, 7).map((x) => x.status),
    ['Ready', 'Backlog', 'In progress', 'Blocked', 'In review', 'Done', 'Done'],
  );
  assert.equal(rows[5].iteration_start, '2026-11-09');
  assert.equal(rows[6].iteration_start, null);
  assert.equal(rows[2].iteration_start, '2026-11-23');
  assert.equal(rows[2].allocation_basis, 'current_planning');
  assert.deepEqual(
    rows.filter((x) => x.kind === 'issue').map((x) => [x.issue, x.owner, x.status]),
    [
      [43, 'christophe', 'In progress'],
      [83, 'tatiana', 'In progress'],
      [84, 'christophe', 'In progress'],
    ],
  );
});
test('status configuration retains every existing option ID; iterations preserve existing identities and become a no-op', () => {
  const { project } = fixture();
  const ops = configurationChanges(project, dates);
  assert.deepEqual(ops[0].input.singleSelectOptions.slice(0, 5), project.fields.nodes[0].options);
  assert.equal(ops[0].input.singleSelectOptions.at(-1).name, 'Blocked');
  assert.deepEqual(
    ops[1].input.iterationConfiguration.iterations.map((x) => x.startDate),
    dates,
  );
  configure(project);
  assert.equal(configurationChanges(project, dates).length, 0);
});

test('F-510: known added issues keep their content and assignments and map current state; unknown cards still refuse', () => {
  const { project, plan } = fixture();
  configure(project);
  for (const number of [128, 129, 169]) {
    const item = JSON.parse(JSON.stringify(project.items.at(-1)));
    item.id = 'issue-item-' + number;
    Object.assign(item.content, {
      id: 'issue-' + number,
      number,
      state: number === 128 ? 'CLOSED' : 'OPEN',
      assignees: { nodes: [{ id: 'user-joey' }] },
    });
    project.items.push(item);
  }
  const before = JSON.parse(JSON.stringify(project));
  const rows = planNative(project, plan, dates, {});
  assert.deepEqual(
    rows
      .filter((row) => [128, 129, 169].includes(row.issue))
      .map((row) => [row.issue, row.owner, row.status]),
    [
      [128, 'christophe', 'Done'],
      [129, 'tatiana', 'In progress'],
      [169, 'tatiana', 'In progress'],
    ],
  );
  const ops = nativeOperations(project, rows);
  const additions = ops.filter((op) => op.name === 'addAssigneesToAssignable');
  assert.equal(
    additions.find((op) => op.input.assignableId === 'issue-169').input.assigneeIds[0],
    'user-tatiana',
  );
  assert.equal(
    ops.some((op) => /remove|delete/i.test(op.name)),
    false,
  );
  assert.deepEqual(project, before);
  project.items.at(-1).content.number = 999;
  assert.throws(() => planNative(project, plan, dates, {}), /Unexpected manual/);
  project.items.at(-1).content.number = 128;
  assert.throws(() => planNative(project, plan, dates, {}), /Unexpected manual/);
  project.items.at(-1).content.number = 169;
  project.items.at(-1).content.repository.nameWithOwner = 'other/repo';
  assert.throws(() => planNative(project, plan, dates, {}), /Unexpected manual/);
});
test('overlapping or duplicate native iterations refuse before writes', () => {
  const { project } = fixture();
  const f = project.fields.nodes.find((x) => x.name === 'Iteration');
  f.configuration.iterations = [
    { id: 'old', title: 'Existing', startDate: '2026-11-04', duration: 7 },
  ];
  assert.throws(() => configurationChanges(project, dates), /overlap/);
  f.configuration.iterations = [
    { id: 'x', title: 'A', startDate: dates[0], duration: 7 },
    { id: 'y', title: 'B', startDate: dates[0], duration: 7 },
  ];
  assert.throws(() => configurationChanges(project, dates), /Duplicate/);
});
test('owner identity mismatch, foreign/public target and unexpected manual card fail before mutation', () => {
  for (const change of [
    (p) => {
      p.public = true;
    },
    (p) => {
      p.url = 'https://github.com/users/other/projects/4';
    },
    (p) => {
      p.users.christophe.login = 'other';
    },
    (p) => {
      p.items.at(-1).content.number = 999;
    },
  ]) {
    const { project, plan } = fixture();
    change(project);
    assert.throws(() => planNative(project, plan, dates, {}));
  }
});
test('native operations use real assignees and numeric estimates, preserve content, then calculate zero repeat writes', () => {
  const { project, plan } = fixture();
  configure(project);
  const rows = planNative(project, plan, dates, {});
  const before = project.items.map((x) => ({
    id: x.id,
    title: x.content.title,
    body: x.content.body,
  }));
  const ops = nativeOperations(project, rows);
  assert.ok(
    ops.some(
      (x) => x.name === 'updateProjectV2DraftIssue' && x.input.assigneeIds[0] === 'user-christophe',
    ),
  );
  assert.ok(
    ops.some(
      (x) =>
        x.name === 'addAssigneesToAssignable' &&
        x.input.assignableId === 'issue-83' &&
        x.input.assigneeIds[0] === 'user-tatiana',
    ),
  );
  assert.ok(ops.some((x) => x.input.value?.number));
  emulate(project, ops);
  assert.deepEqual(
    project.items.map((x) => ({ id: x.id, title: x.content.title, body: x.content.body })),
    before,
  );
  assert.equal(nativeOperations(project, rows).length, 0);
});
test('unresolved iteration/status acknowledgements never become field writes', () => {
  const { project, plan } = fixture();
  const rows = planNative(project, plan, dates, {});
  assert.throws(() => nativeOperations(project, rows), /Unresolved/);
});
test('a failed write batch is not blindly retried or reported as verified', async () => {
  const { project, plan } = fixture();
  configure(project);
  const rows = planNative(project, plan, dates, {});
  let calls = 0;
  await assert.rejects(
    applyNative(
      async () => {
        calls++;
        throw new Error('Synthetic interrupted batch');
      },
      project,
      rows,
      dates,
    ),
    /interrupted/,
  );
  assert.equal(calls, 1);
});
test('first-done history retains the earliest repository status; current planning cannot rewrite that date', () => {
  const md = (status) =>
    `### C-01 Synthetic\n- Owner: christophe\n- Status: ${status}\n- Needs: none\n`;
  assert.deepEqual(
    firstDone([
      { date: '2026-11-01', markdown: md('todo') },
      { date: '2026-11-10', markdown: md('done') },
      { date: '2026-11-20', markdown: md('done') },
    ]),
    { 'C-01': '2026-11-10' },
  );
});
test('CLI is read-only by default and requires explicit native-field authority and workspace output paths', () => {
  assert.equal(options([]).apply, false);
  assert.throws(() => options(['--apply']));
  assert.equal(options(['--apply', '--native-fields']).apply, true);
  assert.throws(() => options(['--out', '../outside.json']));
  assert.throws(() => options(['--ref', '--delete']));
  const config = JSON.parse(
    readFileSync(new URL('../project-native-board.json', import.meta.url), 'utf8'),
  );
  assert.deepEqual(config.meeting_dates, dates);
});
