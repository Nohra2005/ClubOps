/** Synthetic state + cookie must survive actual container replacement on the named local volume. */
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, URL } from 'node:url';
import process from 'node:process';
import { log } from 'node:console';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const project = process.env.CLUBOPS_COMPOSE_TEST_PROJECT;
if (!project || !/^clubops-(ci|bonus-check)(-[a-z0-9]+)?$/.test(project))
  throw new Error(
    'Use an isolated clubops-ci or clubops-bonus-check project for this destructive container check.',
  );
const base = new URL(process.env.CLUBOPS_COMPOSE_URL ?? 'http://127.0.0.1:8080');
assert(base.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(base.hostname));
const docker = process.env.DOCKER_BIN ?? 'docker';
const compose = ['compose', '--project-name', project, '--file', join(root, 'docker-compose.yml')];
const run = (args) =>
  execFileSync(docker, args, {
    cwd: root,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
const before = run([...compose, 'ps', '-q', 'app']);
assert(before, 'Start the isolated Compose app first.');
const environment = JSON.parse(run(['inspect', before, '--format', '{{json .Config.Env}}']));
for (const flag of ['CLUBOPS_WEB_DEV_LOGIN=1', 'CLUBOPS_DEV_LOGIN=1', 'CLUBOPS_COOKIE_SECURE=0'])
  assert(environment.includes(flag), 'The target must be the local development image.');
// Do not reuse a keep-alive socket across the intentional container replacement.
const headers = {
  'X-Requested-With': 'ClubOps',
  'Content-Type': 'application/json',
  Connection: 'close',
};
const signIn = await globalThis.fetch(new URL('/api/auth/dev', base), {
  method: 'POST',
  headers,
  body: JSON.stringify({ email: 'president@example.com' }),
});
assert.equal(signIn.status, 200);
headers.Cookie = signIn.headers.getSetCookie()[0].split(';')[0];
const response = await globalThis.fetch(new URL('/api/cabinet', base), {
  method: 'POST',
  headers,
  body: JSON.stringify({
    name: 'Compose Synthetic Check',
    email: `compose-${randomUUID()}@example.com`,
    role: 'events',
  }),
});
assert(response.ok, 'Synthetic member creation failed.');
const member = await response.json();
run([...compose, 'up', '--force-recreate', '--detach', '--wait', '--no-build']);
assert.notEqual(
  run([...compose, 'ps', '-q', 'app']),
  before,
  'A different container must be created.',
);
const cabinet = await globalThis.fetch(new URL('/api/cabinet', base), { headers });
assert.equal(
  cabinet.status,
  200,
  'The volume-backed signing key must preserve the existing session.',
);
assert(
  (await cabinet.json()).some((row) => row.member_id === member.member_id),
  'SQLite record was lost.',
);
const cleanup = await globalThis.fetch(new URL('/api/cabinet', base), {
  method: 'DELETE',
  headers,
  body: JSON.stringify({ member_id: member.member_id }),
});
assert(cleanup.ok, 'Synthetic check record could not be removed.');
log(
  'Compose verified: container replaced; SQLite state and existing session survived; synthetic check record removed.',
);
