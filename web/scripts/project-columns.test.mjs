import assert from 'node:assert/strict';
import { test } from 'node:test';
import { configureColumns, columnsView } from './project-columns.mjs';
import { marker } from './project-plan.mjs';
const plan = { owner: 'synthetic', repository: 'synthetic/clubops', cards: [] };
function fixture() {
  const fields = ['Title', 'Status', 'Owner', 'Task ID', 'Needs', 'Sprint'].map((name, i) => ({
    id: `f${i}`,
    name,
  }));
  const state = {
    id: 'p',
    url: 'https://github.com/users/synthetic/projects/1',
    public: false,
    closed: false,
    viewerCanUpdate: true,
    readme: `${marker}\n${plan.repository}\n`,
    fields: { nodes: fields, pageInfo: { hasNextPage: false } },
    views: {
      nodes: [{ id: 'manual', name: 'Original view', number: 1, layout: 'TABLE_LAYOUT' }],
      pageInfo: { hasNextPage: false },
    },
  };
  const calls = [];
  const api = async (query) =>
    query.includes('query Board(')
      ? { user: { projectV2: globalThis.structuredClone(state) } }
      : { node: { items: { nodes: [], pageInfo: { hasNextPage: false } } } };
  const rows = fields.map((field, i) => ({
    id: i + 1,
    node_id: field.id,
    data_type: i === 0 ? 'title' : 'text',
  }));
  const rest = async (path, method, body) => {
    calls.push({ path, method, body });
    if (method === 'GET') return rows;
    assert.deepEqual(body.vertical_group_by, [2]);
    assert.deepEqual(body.group_by, []);
    state.views.nodes.push({
      id: 'new',
      number: 2,
      name: body.name,
      layout: 'BOARD_LAYOUT',
      verticalGroupByFields: { nodes: [fields[1]], pageInfo: { hasNextPage: false } },
    });
    return { value: { number: 2 } };
  };
  return { state, calls, api, rest, rows };
}
test('creates status columns via REST and verifies the vertical field with GraphQL; repeat is a no-op', async () => {
  const f = fixture();
  const manual = globalThis.structuredClone(f.state.views.nodes[0]);
  const result = await configureColumns(f.api, f.rest, plan, 1);
  assert.equal(result.verified, true);
  assert.equal(result.url, 'https://github.com/users/synthetic/projects/1/views/2');
  assert.deepEqual(f.state.views.nodes[0], manual);
  assert.equal((await configureColumns(f.api, f.rest, plan, 1)).created, false);
  assert.equal(f.calls.filter((call) => call.method === 'POST').length, 1);
});
test('horizontal grouping is never accepted as the status column field', async () => {
  const f = fixture();
  f.state.views.nodes.push({
    id: 'wrong',
    name: columnsView,
    layout: 'BOARD_LAYOUT',
    groupByFields: { nodes: [f.state.fields.nodes[1]] },
    verticalGroupByFields: { nodes: [f.state.fields.nodes[2]] },
  });
  await assert.rejects(configureColumns(f.api, f.rest, plan, 1), /refusing to overwrite/);
  assert.equal(f.calls.length, 0);
});
test('incomplete REST fields or invalid numeric identities refuse before creating a view', async () => {
  for (const kind of ['missing', 'invalid']) {
    const f = fixture();
    if (kind === 'missing') f.rows.pop();
    else f.rows[1].id = 'not-an-integer';
    await assert.rejects(configureColumns(f.api, f.rest, plan, 1));
    assert.equal(f.calls.filter((call) => call.method === 'POST').length, 0);
  }
});
test('an uncertain POST is resumed by read-back without making a second view', async () => {
  const f = fixture();
  const rest = async (...args) => {
    const result = await f.rest(...args);
    if (args[1] === 'POST') throw new Error('Synthetic lost response');
    return result;
  };
  await assert.rejects(configureColumns(f.api, rest, plan, 1), /lost response/);
  assert.equal((await configureColumns(f.api, f.rest, plan, 1)).created, false);
  assert.equal(f.state.views.nodes.length, 2);
});
test('changed original view metadata refuses a successful column receipt', async () => {
  const f = fixture();
  const rest = async (...args) => {
    const result = await f.rest(...args);
    if (args[1] === 'POST') f.state.views.nodes[0].name = 'Changed';
    return result;
  };
  await assert.rejects(configureColumns(f.api, rest, plan, 1), /manual views/);
});
