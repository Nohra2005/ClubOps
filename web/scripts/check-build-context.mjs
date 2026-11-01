/** Exercise Docker's actual ignore rules with synthetic canaries; never read private file contents. */
import { mkdirSync, mkdtempSync, readdirSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import process from 'node:process';
import { log } from 'node:console';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const output = join(root, 'output');
mkdirSync(output, { recursive: true });
mkdirSync(join(root, 'web/node_modules'), { recursive: true });
const destination = mkdtempSync(join(output, 'docker-context-'));
const canaries = [
  join(root, 'web/.env.context-canary'),
  join(root, 'web/node_modules/clubops-context-canary.txt'),
];
const created = [];
try {
  for (const path of canaries) {
    writeFileSync(path, 'SYNTHETIC_CONTEXT_CANARY=not-a-secret\n', { flag: 'wx' });
    created.push(path);
  }
  const result = spawnSync(
    process.env.DOCKER_BIN ?? 'docker',
    ['build', '--target', 'build-context-check', '--output', `type=local,dest=${destination}`, '.'],
    { cwd: root, stdio: 'pipe', encoding: 'utf8' },
  );
  if (result.status !== 0)
    throw new Error(result.stderr || 'Docker context check could not start.');
  const paths = readdirSync(destination, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) =>
      relative(destination, join(entry.parentPath, entry.name)).replaceAll('\\', '/'),
    );
  const forbidden = paths.filter(
    (path) =>
      path
        .split('/')
        .some((part) =>
          [
            '.git',
            'node_modules',
            '__pycache__',
            'output',
            'test-results',
            'playwright-report',
          ].includes(part),
        ) ||
      /(^|\/)\.env($|\.)|\.(pyc|db|sqlite|sqlite3)$/.test(path) ||
      /^(data\/(private|raw|app)|tests|eval|traces)\//.test(path),
  );
  if (forbidden.length) throw new Error(`Disallowed build inputs: ${forbidden.join(', ')}`);
  for (const required of ['pyproject.toml', 'src/clubops/api/app.py', 'web/src/main.tsx']) {
    if (!paths.includes(required)) throw new Error(`Missing required build input: ${required}`);
  }
  log(
    `Docker context verified: ${paths.length} files; private/runtime/dependency canaries excluded.`,
  );
} finally {
  for (const path of created) unlinkSync(path);
}
