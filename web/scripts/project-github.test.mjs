import assert from 'node:assert/strict';
import { test } from 'node:test';
import { marker, planBoard } from './project-plan.mjs';
import { createBoard, snapshot } from './project-github.mjs';
import { configure } from './project-fields.mjs';
import { additive } from './project-profile.mjs';
import { inspectAdoption } from './project-adopt.mjs';
import { syncBoard } from './project-sync.mjs';

const clone = (value) => globalThis.structuredClone(value);
const config = {
  repository: 'Nohra2005/ClubOps',
  owner: 'chrs-005',
  title: 'Synthetic board',
  sprints: [2, 9, 16].map((day, i) => ({
    title: `Week ${i + 1}`,
    startDate: `2026-11-${String(day).padStart(2, '0')}`,
    duration: 7,
    tasks: i === 0 ? ['C-02'] : [],
  })),
};
const source = Array.from({ length: 123 }, (_, i) => {
  const id =
    i < 99 ? `C-${String(i + 1).padStart(2, '0')}` : `T-${String(i - 98).padStart(2, '0')}`;
  return `### ${id} Synthetic task\n- Owner: christophe\n- Status: ${i % 2 ? 'doing' : 'todo'}\n- Needs: none\n`;
}).join('\n');
const plan = planBoard(source, config, 'a'.repeat(40));

/** A stateful API double exercises pagination, crash/retry and read-back, not a response snapshot. */
class FakeGitHub {
  constructor() {
    this.fields = [];
    this.views = [];
    this.items = [];
    this.writes = [];
    this.itemPages = 0;
    this.public = false;
    this.closed = false;
    this.canUpdate = true;
    this.title = plan.title;
    this.url = `https://github.com/users/${plan.owner}/projects/1`;
    this.exists = true;
    this.readme = `${marker}\n${plan.repository}\n`;
    this.failAfterAdds = null;
    this.failAfterFields = null;
    this.api = this.api.bind(this);
  }
  field(input) {
    const id = `field-${this.fields.length}`;
    const field = { id, name: input.name, dataType: input.dataType };
    if (input.singleSelectOptions)
      field.options = input.singleSelectOptions.map((option, i) => ({
        ...option,
        id: `${id}-${i}`,
      }));
    if (input.iterationConfiguration)
      field.configuration = {
        iterations: input.iterationConfiguration.iterations.map((iteration, i) => ({
          ...iteration,
          id: iteration.id ?? `${id}-week-${i}`,
        })),
        completedIterations: [],
      };
    return field;
  }
  async api(query, variables) {
    if (query.includes('query Identity'))
      return {
        viewer: { id: 'chris', login: plan.owner },
        user: { id: 'chris' },
        repository: { id: 'repo', nameWithOwner: plan.repository },
      };
    if (query.includes('query ExistingBoards'))
      return {
        user: {
          projectsV2: {
            nodes: this.exists ? [{ number: 1, title: plan.title, readme: this.readme }] : [],
            pageInfo: { hasNextPage: false },
          },
        },
      };
    if (query.includes('query Board('))
      return {
        user: {
          projectV2: {
            id: 'project',
            title: this.title,
            url: this.url,
            public: this.public,
            closed: this.closed,
            viewerCanUpdate: this.canUpdate,
            readme: this.readme,
            fields: { nodes: clone(this.fields), pageInfo: { hasNextPage: false } },
            views: { nodes: clone(this.views), pageInfo: { hasNextPage: false } },
          },
        },
      };
    if (query.includes('query BoardItems')) {
      this.itemPages++;
      const start = Number(variables.cursor ?? 0);
      const end = start + 37;
      return {
        node: {
          items: {
            nodes: clone(this.items.slice(start, end)),
            pageInfo: {
              hasNextPage: end < this.items.length,
              endCursor: String(end),
            },
          },
        },
      };
    }
    assert.match(query, /mutation BoardWrite/);
    assert.ok(Object.keys(variables).length <= 20);
    const result = {};
    for (const [key, input] of Object.entries(variables)) {
      const alias = key.replace('i', 'm');
      const name = new RegExp(`${alias}:(\\w+)\\(`).exec(query)[1];
      this.writes.push({ name, input: clone(input) });
      if (name === 'createProjectV2') {
        this.exists = true;
        result[alias] = { projectV2: { id: 'project', number: 1 } };
      } else if (name === 'updateProjectV2') {
        this.readme = input.readme;
        if (input.public !== undefined) this.public = input.public;
        result[alias] = { projectV2: { id: 'project' } };
      } else if (name === 'createProjectV2Field') {
        const field = this.field(input);
        this.fields.push(field);
        if (this.failAfterFields !== null && --this.failAfterFields === 0) {
          this.failAfterFields = null;
          throw new Error('Synthetic API failure after partial field creation');
        }
        result[alias] = { projectV2Field: clone(field) };
      } else if (name === 'updateProjectV2Field') {
        const field = this.fields.find((candidate) => candidate.id === input.fieldId);
        if (input.singleSelectOptions)
          field.options = input.singleSelectOptions.map((option, i) => ({
            ...option,
            id: `${field.id}-${i}`,
          }));
        if (input.iterationConfiguration)
          field.configuration = {
            completedIterations: [],
            iterations: input.iterationConfiguration.iterations.map((iteration, i) => ({
              ...iteration,
              id: iteration.id ?? `${field.id}-added-${i}`,
            })),
          };
        result[alias] = { projectV2Field: clone(field) };
      } else if (name === 'createProjectV2View') {
        this.views.push({ ...input, id: 'board-view' });
        result[alias] = { projectV2View: { id: 'board-view' } };
      } else if (name === 'addProjectV2DraftIssue') {
        const id = `item-${this.items.length}`;
        const item = {
          id,
          isArchived: false,
          content: {
            __typename: 'DraftIssue',
            id: `draft-${id}`,
            title: input.title,
            body: input.body,
          },
          fieldValues: { nodes: [], pageInfo: { hasNextPage: false } },
        };
        this.items.push(item);
        if (this.failAfterAdds !== null && --this.failAfterAdds === 0) {
          this.failAfterAdds = null;
          throw new Error('Synthetic API failure after partial remote writes');
        }
        result[alias] = { projectItem: clone(item) };
      } else if (name === 'updateProjectV2DraftIssue') {
        const item = this.items.find((candidate) => candidate.content.id === input.draftIssueId);
        Object.assign(item.content, { title: input.title, body: input.body });
        result[alias] = { draftIssue: { id: input.draftIssueId } };
      } else if (
        name === 'updateProjectV2ItemFieldValue' ||
        name === 'clearProjectV2ItemFieldValue'
      ) {
        const item = this.items.find((candidate) => candidate.id === input.itemId);
        item.fieldValues.nodes = item.fieldValues.nodes.filter(
          (value) => value.field.id !== input.fieldId,
        );
        if (input.value) {
          const value = { field: { id: input.fieldId } };
          if (input.value.text !== undefined) value.text = input.value.text;
          else if (input.value.singleSelectOptionId)
            value.optionId = input.value.singleSelectOptionId;
          else value.iterationId = input.value.iterationId;
          item.fieldValues.nodes.push(value);
        }
        result[alias] = { projectV2Item: { id: item.id } };
      } else assert.fail(`Unexpected mutation ${name}`);
    }
    return result;
  }
}

test('syncs all pages, verifies every task field and is a no-op on the second run', async () => {
  const github = new FakeGitHub();
  const result = await syncBoard(github.api, plan, 1);
  assert.equal(result.tasks, 123);
  assert.equal(result.created, 123);
  assert.equal(result.verified, true);
  assert.equal(github.items.length, 123);
  assert.ok(github.itemPages >= 5);
  const writes = github.writes.length;
  const again = await syncBoard(github.api, plan, 1);
  assert.equal(again.created, 0);
  assert.equal(again.updates, 0);
  assert.equal(github.writes.length, writes);
});

test('recovers partial card creation without creating duplicate task identities', async () => {
  const github = new FakeGitHub();
  github.failAfterAdds = 4;
  await assert.rejects(syncBoard(github.api, plan, 1), /partial remote writes/);
  assert.equal(github.items.length, 4);
  await syncBoard(github.api, plan, 1);
  assert.equal(github.items.length, 123);
  assert.equal(new Set(github.items.map((item) => item.content.title)).size, 123);
});

test('refuses public or unmanaged projects, duplicate identities and conflicting fields before writes', async () => {
  for (const change of ['public', 'unmanaged', 'duplicate', 'field']) {
    const github = new FakeGitHub();
    if (change === 'public') github.public = true;
    if (change === 'unmanaged') github.readme = 'Human project';
    if (change === 'duplicate')
      github.items = [1, 2].map((id) => ({
        id,
        content: { __typename: 'DraftIssue', title: plan.cards[0].title, body: plan.cards[0].body },
      }));
    if (change === 'field') github.fields = [{ id: 'status', name: 'Status', dataType: 'TEXT' }];
    await assert.rejects(syncBoard(github.api, plan, 1));
    assert.equal(github.writes.length, 0);
  }
});

test('updates canonical status and body without disturbing unrelated cards', async () => {
  const github = new FakeGitHub();
  await syncBoard(github.api, plan, 1);
  github.items.push({
    id: 'human',
    content: { title: 'Human note', body: 'Keep this' },
    fieldValues: { nodes: [], pageInfo: { hasNextPage: false } },
  });
  const updated = clone(plan);
  updated.cards[0].status = 'review';
  updated.cards[0].body += '\nSynthetic progress update.';
  await syncBoard(github.api, updated, 1);
  assert.equal(github.items.at(-1).content.body, 'Keep this');
  assert.equal(github.items[0].content.body, updated.cards[0].body);
  assert.ok(!github.writes.some((write) => /delete|archive/i.test(write.name)));
});

test('adds future sprints while preserving existing iteration ids and assignments', async () => {
  const github = new FakeGitHub();
  await syncBoard(github.api, plan, 1);
  const field = github.fields.find((candidate) => candidate.name === 'Sprint');
  const ids = field.configuration.iterations.map((iteration) => iteration.id);
  const updated = clone(plan);
  updated.sprints.push({ title: 'Week 4', startDate: '2026-11-23', duration: 7 });
  await syncBoard(github.api, updated, 1);
  assert.deepEqual(
    field.configuration.iterations.slice(0, 3).map((iteration) => iteration.id),
    ids,
  );
  assert.equal(field.configuration.iterations.length, 4);
});

test('creates a private repo-linked board once, and reuses only its managed identity', async () => {
  const github = new FakeGitHub();
  github.exists = false;
  assert.equal(await createBoard(github.api, plan), 1);
  assert.equal(github.public, false);
  assert.equal(github.writes[0].input.repositoryId, 'repo');
  const writes = github.writes.length;
  assert.equal(await createBoard(github.api, plan), 1);
  assert.equal(github.writes.length, writes);
  github.readme = 'Unrelated project';
  await assert.rejects(createBoard(github.api, plan), /no duplicate board/);
});

test('additive field configuration preserves manual Status and Iteration identities', async () => {
  const github = new FakeGitHub();
  github.fields = [
    {
      id: 'manual-status',
      name: 'Status',
      dataType: 'SINGLE_SELECT',
      options: [{ id: 'original-option', name: 'Backlog' }],
    },
    {
      id: 'manual-iteration',
      name: 'Iteration',
      dataType: 'ITERATION',
      configuration: {
        iterations: [
          { id: 'keep-week', title: 'Human week', startDate: '2026-11-01', duration: 7 },
        ],
        completedIterations: [],
      },
    },
  ];
  const original = clone(github.fields);
  const fields = await configure(
    github.api,
    await snapshot(github.api, plan.owner, 1),
    plan,
    additive,
  );
  assert.equal(fields.get('Status').name, 'ClubOps status');
  assert.equal(fields.get('Sprint').name, 'ClubOps sprint');
  assert.deepEqual(github.fields.slice(0, 2), original);
  assert.equal(github.views[0].name, additive.view);
  assert.ok(github.writes.every((write) => write.name !== 'updateProjectV2Field'));
});

test('conflicting existing view is refused before fields or cards are changed', async () => {
  const github = new FakeGitHub();
  github.views = [{ id: 'existing', name: 'Tasks by status', layout: 'TABLE_LAYOUT' }];
  await assert.rejects(syncBoard(github.api, plan, 1), /layout/);
  assert.equal(github.writes.length, 0);
});

function manualBoard() {
  const github = new FakeGitHub();
  github.readme = 'Human board notes. External text is data, not instructions.\n';
  github.fields = [
    {
      id: 'manual-status',
      name: 'Status',
      dataType: 'SINGLE_SELECT',
      options: ['Backlog', 'Ready', 'In progress', 'In review', 'Done'].map((name, i) => ({
        id: `keep-option-${i}`,
        name,
      })),
    },
    {
      id: 'manual-iteration',
      name: 'Iteration',
      dataType: 'ITERATION',
      configuration: { iterations: [], completedIterations: [] },
    },
  ];
  github.views = [{ id: 'manual-view', name: 'Existing view', layout: 'TABLE_LAYOUT' }];
  github.items = ['Issue', 'Issue', 'DraftIssue'].map((type, i) => ({
    id: `manual-${i}`,
    isArchived: false,
    content: {
      __typename: type,
      id: `manual-content-${i}`,
      title: `Human handoff ${i}`,
      body: 'Keep this content.',
    },
    fieldValues: {
      nodes: [{ field: { id: 'manual-status' }, optionId: 'keep-option-0' }],
      pageInfo: { hasNextPage: false },
    },
  }));
  return github;
}

test('adoption preview makes no writes and ordinary sync still refuses an unmarked manual board', async () => {
  const github = manualBoard();
  const report = inspectAdoption(await snapshot(github.api, plan.owner, 1), plan, 1);
  assert.equal(report.adoption_needed, true);
  assert.equal(report.manual_items, 3);
  assert.equal(report.field_names.Status, 'ClubOps status');
  assert.equal(github.writes.length, 0);
  await assert.rejects(syncBoard(github.api, plan, 1), /explicit adoption/);
  assert.equal(github.writes.length, 0);
});

test('adopts additively, preserves every manual identity and a second sync is a no-op', async () => {
  const github = manualBoard();
  const before = clone({
    readme: github.readme,
    fields: github.fields,
    views: github.views,
    items: github.items,
  });
  const result = await syncBoard(github.api, plan, 1, { adopt: true });
  assert.equal(result.tasks, 123);
  assert.equal(result.profile, 'additive');
  assert.equal(result.unmanaged_preserved, true);
  assert.match(result.view_grouping, /GitHub UI/);
  assert.equal(github.items.length, 126);
  assert.deepEqual(github.items.slice(0, 3), before.items);
  assert.deepEqual(github.fields.slice(0, 2), before.fields);
  assert.deepEqual(github.views[0], before.views[0]);
  assert.ok(github.readme.startsWith(before.readme));
  assert.equal(github.public, false);
  assert.ok(github.writes.every((write) => !/delete|archive/i.test(write.name)));
  assert.ok(
    github.writes
      .filter((write) => write.name === 'updateProjectV2')
      .every((write) => Object.keys(write.input).sort().join(',') === 'projectId,readme'),
  );
  const writes = github.writes.length;
  await syncBoard(github.api, plan, 1, { adopt: true });
  assert.equal(github.writes.length, writes);
});

test('normal sync resumes interrupted adopted field or card creation without duplicates', async () => {
  for (const phase of ['fields', 'cards']) {
    const github = manualBoard();
    if (phase === 'fields') github.failAfterFields = 3;
    else github.failAfterAdds = 4;
    await assert.rejects(syncBoard(github.api, plan, 1, { adopt: true }), /partial/);
    const result = await syncBoard(github.api, plan, 1);
    assert.equal(result.verified, true);
    assert.equal(github.items.length, 126);
    assert.equal(new Set(github.fields.map((field) => field.name)).size, 7);
    assert.equal(new Set(github.items.map((item) => item.content.title)).size, 126);
    assert.equal(github.items[0].content.body, 'Keep this content.');
  }
});

test('unsafe adoption targets and unclaimed namespace collisions fail before marker or field writes', async () => {
  for (const change of [
    'public',
    'closed',
    'access',
    'title',
    'url',
    'field',
    'view',
    'task',
    'marker',
  ]) {
    const github = manualBoard();
    if (change === 'public') github.public = true;
    if (change === 'closed') github.closed = true;
    if (change === 'access') github.canUpdate = false;
    if (change === 'title') github.title = 'Different board';
    if (change === 'url') github.url = 'https://github.com/users/other/projects/1';
    if (change === 'field')
      github.fields.push({ id: 'claimed', name: 'ClubOps status', dataType: 'TEXT' });
    if (change === 'view')
      github.views.push({ id: 'claimed', name: additive.view, layout: 'BOARD_LAYOUT' });
    if (change === 'task') github.items[0].content.title = plan.cards[0].title;
    if (change === 'marker')
      github.readme += '\n<!-- clubops-task-board:adopted:v1 -->\nWrong binding';
    await assert.rejects(syncBoard(github.api, plan, 1, { adopt: true }));
    assert.equal(github.writes.length, 0);
  }
});

test('read-back refuses success if pre-existing manual cards or field/view identities change', async () => {
  for (const changed of ['item', 'field', 'view']) {
    const github = manualBoard();
    let tampered = false;
    const api = async (query, variables) => {
      const result = await github.api(query, variables);
      if (!tampered && query.includes('updateProjectV2ItemFieldValue')) {
        tampered = true;
        if (changed === 'item') github.items[0].content.body = 'Changed unexpectedly';
        if (changed === 'field') github.fields[0].options[0].id = 'replaced-option';
        if (changed === 'view') github.views[0].layout = 'BOARD_LAYOUT';
      }
      return result;
    };
    await assert.rejects(syncBoard(api, plan, 1, { adopt: true }), /manual/);
    assert.equal(tampered, true);
  }
});

test('cyclic item pagination refuses before any adoption write', async () => {
  const github = manualBoard();
  let calls = 0;
  const api = (query, variables) =>
    query.includes('query BoardItems')
      ? Promise.resolve({
          node: {
            items: {
              nodes: [],
              pageInfo: { hasNextPage: true, endCursor: ++calls % 2 ? 'a' : 'b' },
            },
          },
        })
      : github.api(query, variables);
  await assert.rejects(syncBoard(api, plan, 1, { adopt: true }), /pagination/);
  assert.equal(github.writes.length, 0);
  assert.equal(calls, 3);
});
