import assert from 'node:assert/strict';
import { test } from 'node:test';
import { options } from './project-board.mjs';

test('defaults to a read-only plan and requires an explicit target for writes', () => {
  assert.equal(options([]).apply, false);
  assert.equal(options([]).ref, 'origin/main');
  assert.equal(options(['--apply', '--create']).create, true);
  assert.equal(options(['--apply', '--project-number', '1']).number, 1);
  assert.equal(options(['--adopt', '--project-number', '4']).apply, false);
  assert.equal(options(['--adopt', '--apply', '--project-number', '4']).adopt, true);
  for (const args of [
    ['--apply'],
    ['--create'],
    ['--ref', '-unsafe'],
    ['--ref'],
    ['--project-number', '0'],
    ['--apply', '--create', '--project-number', '1'],
    ['--unknown'],
    ['--adopt'],
    ['--adopt', '--create', '--apply'],
  ])
    assert.throws(() => options(args));
});
