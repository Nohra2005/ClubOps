import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { managedItems, marker, parseTasks, planBoard } from './project-plan.mjs';

const task = (id, owner = 'christophe', status = 'todo', needs = 'none') =>
  `### ${id} Synthetic task\n- Owner: ${owner}\n- Status: ${status}\n- Needs: ${needs}\n- What: Synthetic work.\n- Done when: Tested.\n`;
const source = task('C-01') + task('C-02', 'christophe', 'doing', 'C-01') + task('J-01', 'joey');
const ref = 'a'.repeat(40);
const config = {
  repository: 'Nohra2005/ClubOps',
  owner: 'chrs-005',
  title: 'Synthetic board',
  sprints: [2, 9, 16].map((day, index) => ({
    title: `Week ${index + 1}`,
    startDate: `2026-11-${String(day).padStart(2, '0')}`,
    duration: 7,
    tasks: index === 0 ? ['C-02'] : [],
  })),
};

test('validates task identities, owners/statuses and dependencies before any remote action', () => {
  assert.equal(parseTasks(source).length, 3);
  assert.equal(parseTasks(source + `<!-- ${task('C-99')} -->`).length, 3);
  for (const invalid of [
    source + task('C-01'),
    task('C-01', 'unknown'),
    task('C-01', 'christophe', 'almost'),
    task('C-01', 'christophe', 'todo', 'T-99'),
    'no task headings',
  ])
    assert.throws(() => parseTasks(invalid));
});

test('pins board source, hashes exact input and retains blockers without inventing completion', () => {
  const plan = planBoard(source, config, ref);
  assert.equal(plan.cards[1].sprint, 'Week 1');
  assert.equal(plan.cards[0].sprint, null);
  assert.equal(plan.cards[1].status, 'doing');
  assert.deepEqual(plan.cards[1].needs, ['C-01']);
  assert.match(plan.cards[1].body, /Sprint assignments are tentative/);
  assert.match(plan.source.url, new RegExp(ref));
  assert.notEqual(plan.source.sha256, planBoard(source + '\n', config, ref).source.sha256);
});

test('refuses ambiguous, overlapping or invalid sprint plans', () => {
  for (const change of [
    { tasks: ['C-99'] },
    { tasks: ['C-02'] },
    { startDate: '2026-11-03' },
    { startDate: '2026-02-30' },
    { duration: 14 },
    { title: 'Week 1' },
  ]) {
    const changed = structuredClone(config);
    Object.assign(changed.sprints[1], change);
    assert.throws(() => planBoard(source, changed, ref));
  }
  assert.throws(() => planBoard(source, config, 'main'));
});

test('leaves human-created cards alone and rejects duplicate managed identities', () => {
  const content = {
    __typename: 'DraftIssue',
    id: 'draft-1',
    title: 'C-01: Synthetic',
    body: `${marker}\nTask: C-01\n`,
  };
  const item = { id: 'item-1', content };
  assert.equal(managedItems([item, { content: { body: 'human notes' } }]).size, 1);
  assert.throws(() => managedItems([item, { ...item, id: 'item-2' }]));
  assert.throws(() => managedItems([{ ...item, isArchived: true }]));
});

test('the committed sprint plan validates against the actual canonical task file', () => {
  const markdown = readFileSync(new URL('../../TASKS.md', import.meta.url), 'utf8');
  const settings = JSON.parse(
    readFileSync(new URL('../project-board.json', import.meta.url), 'utf8'),
  );
  const plan = planBoard(markdown, settings, ref);
  assert.equal(plan.cards.length, parseTasks(markdown).length);
  assert.ok(plan.cards.length > 70);
});
