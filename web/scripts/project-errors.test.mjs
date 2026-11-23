import assert from 'node:assert/strict';
import { test } from 'node:test';
import { publicFailure } from './project-errors.mjs';
test('timeout and throttle guidance preserves the explicit read-back/retry boundary', () => {
  assert.match(
    publicFailure({ stdout: 'Timeout', stderr: 'synthetic-private-diagnostic' }, null).message,
    /Resume after read-back/,
  );
  assert.match(
    publicFailure(
      { stdout: '', stderr: 'submitted too quickly synthetic-private-diagnostic' },
      null,
    ).message,
    /Wait before resuming/,
  );
});
test('only known error categories are emitted, never diagnostics or arbitrary error types', () => {
  const failure = publicFailure(
    { stdout: '', stderr: 'synthetic-secret-value' },
    {
      errors: [
        { type: 'FORBIDDEN', message: 'synthetic-private-body' },
        { type: 'SYNTHETICSECRET', message: 'do not echo' },
      ],
    },
  );
  assert.match(failure.message, /FORBIDDEN/);
  assert.doesNotMatch(failure.message, /synthetic-secret|private-body|SYNTHETICSECRET|do not echo/);
});
test('missing Projects scope receives instructions without echoing credentials', () => {
  const failure = publicFailure(
    { stdout: '', stderr: 'INSUFFICIENT_SCOPES synthetic-secret' },
    null,
  );
  assert.match(failure.message, /gh auth refresh -s project/);
  assert.doesNotMatch(failure.message, /synthetic-secret/);
});
