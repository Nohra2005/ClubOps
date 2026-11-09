import assert from 'node:assert/strict';
import { test } from 'node:test';
import { marker, planBoard } from './project-plan.mjs';
import { createBoard } from './project-github.mjs';
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
    this.exists = true;
    this.readme = `${marker}\n${plan.repository}\n`;
    this.failAfterAdds = null;
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
            url: 'https://github.com/users/synthetic/projects/1',
            public: this.public,
            closed: false,
            viewerCanUpdate: true,
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
        this.public = input.public;
        result[alias] = { projectV2: { id: 'project' } };
      } else if (name === 'createProjectV2Field') {
        const field = this.field(input);
        this.fields.push(field);
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
