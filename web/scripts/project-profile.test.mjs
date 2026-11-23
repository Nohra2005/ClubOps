import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  additive,
  adoptionBlock,
  dedicated,
  profileFor,
  resolveFields,
  preserveUnmanaged,
  assertPreserved,
} from './project-profile.mjs';
import { marker } from './project-plan.mjs';
const plan = { repository: 'synthetic/clubops' };
const project = {
  id: 'project-1',
  public: false,
  readme: 'Human instructions remain data.',
  fields: {
    nodes: [{ id: 'human-status', name: 'Status', options: [{ id: 'keep-id', name: 'Backlog' }] }],
  },
  views: { nodes: [{ id: 'manual-view', name: 'Existing view', layout: 'TABLE_LAYOUT' }] },
  items: [{ id: 'manual-card', content: { title: 'Human task', body: 'Keep this' } }],
};
test('additive markers bind a single project/repository without claiming ordinary fields', () => {
  assert.equal(profileFor(project, plan), null);
  const adopted = {
    ...project,
    readme: `${project.readme}\n\n${adoptionBlock(project, plan)}\n\nTask guide`,
  };
  assert.equal(profileFor(adopted, plan), additive);
  assert.equal(
    profileFor(
      { ...adopted, readme: `${project.readme}\n\n\n${adoptionBlock(project, plan)}\n\nGuide` },
      plan,
    ),
    additive,
  );
  assert.equal(
    profileFor({ ...project, readme: `${marker}\n${plan.repository}\n` }, plan),
    dedicated,
  );
  assert.throws(() => profileFor({ ...adopted, id: 'other-project' }, plan), /mismatched/);
  assert.throws(() => profileFor(adopted, { repository: 'other/repo' }), /mismatched/);
  assert.throws(
    () =>
      profileFor(
        { ...adopted, readme: `${adopted.readme}\n\n${adoptionBlock(project, plan)}` },
        plan,
      ),
    /Ambiguous/,
  );
  assert.equal(resolveFields(project, additive).size, 0);
});
test('read-back proves existing manual content and identities are intact', () => {
  const baseline = preserveUnmanaged(project, additive);
  const expanded = globalThis.structuredClone(baseline);
  expanded.items.push({ id: 'new-manual-card', content: { title: 'New note' } });
  assert.doesNotThrow(() => assertPreserved(baseline, expanded));
  for (const key of ['fields', 'views', 'items']) {
    const changed = globalThis.structuredClone(expanded);
    changed[key][0].id = 'replaced-id';
    assert.throws(() => assertPreserved(baseline, changed), /manual/);
  }
  assert.throws(() => assertPreserved(baseline, { ...expanded, readme: '' }), /description/);
  assert.throws(() => assertPreserved(baseline, { ...expanded, public: true }), /visibility/);
});
