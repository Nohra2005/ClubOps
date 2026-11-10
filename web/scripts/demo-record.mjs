/** Allocate a fresh checked workspace directory before Playwright can clean its output. */
import console from 'node:console';
import { spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { mkdirSync, mkdtempSync, realpathSync } from 'node:fs';
import { createRequire } from 'node:module';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const flags = process.argv.slice(2);
if (flags.length > 1 || (flags.length === 1 && flags[0] !== '--list')) {
  console.error('Use demo:record with no arguments, or --list to check configuration.');
  process.exit(1);
}
const webRoot = realpathSync(fileURLToPath(new URL('../', import.meta.url)));
const projectRoot = realpathSync(resolve(webRoot, '..'));
const artifactRoot = resolve(projectRoot, 'output');
mkdirSync(artifactRoot, { recursive: true });
if (dirname(realpathSync(artifactRoot)) !== projectRoot) {
  console.error('Rehearsal output must stay inside this workspace.');
  process.exit(1);
}
const recordingDir = mkdtempSync(resolve(artifactRoot, 'demo-rehearsal-'));
if (dirname(realpathSync(recordingDir)) !== realpathSync(artifactRoot)) {
  console.error('Invalid rehearsal output directory.');
  process.exit(1);
}
console.log(`Rehearsal artifacts: ${recordingDir}`);
const require = createRequire(import.meta.url);
const result = spawnSync(
  process.execPath,
  [
    require.resolve('@playwright/test/cli'),
    'test',
    '--config',
    resolve(webRoot, 'playwright.demo.config.ts'),
    '--output',
    recordingDir,
    ...flags,
  ],
  { cwd: webRoot, stdio: 'inherit', shell: false },
);
process.exit(result.status ?? 1);
