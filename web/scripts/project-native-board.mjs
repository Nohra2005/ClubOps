/** One explicit run: canonical task mirror, native configuration, assignments and verified read-back. */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import process from 'node:process';
import { log, error } from 'node:console';
import { github } from './project-board.mjs';
import { batch } from './project-github.mjs';
import { parseTasks, planBoard } from './project-plan.mjs';
import { syncBoard } from './project-sync.mjs';
import {
  applyNative,
  configurationChanges,
  nativeOperations,
  nativeSnapshot,
  planNative,
} from './project-native.mjs';

const publicRow = (row) =>
  Object.fromEntries(
    Object.entries(row).filter(([key]) => !['assignee_id', 'content_id'].includes(key)),
  );

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
function git(args) {
  const r = spawnSync('git', args, { cwd: root, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
  if (r.status !== 0) throw new Error('Git source/history unavailable');
  return r.stdout;
}
export function options(args) {
  const value = {
    apply: false,
    native: false,
    ref: 'origin/main',
    out: 'output/native-board-plan.json',
  };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--apply') value.apply = true;
    else if (args[i] === '--native-fields') value.native = true;
    else if (['--ref', '--out'].includes(args[i])) {
      const key = args[i].slice(2);
      const next = args[++i];
      if (!next || next.startsWith('--')) throw new Error('Missing CLI value');
      value[key] = next;
    } else throw new Error('Unknown native board option');
  }
  if (value.apply && !value.native)
    throw new Error('--apply also needs --native-fields to authorize native field writes');
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_./-]*$/.test(value.ref)) throw new Error('Invalid source ref');
  const destination = resolve(root, value.out),
    allowed = resolve(root, 'output');
  if (!destination.startsWith(allowed + '/') && !destination.startsWith(allowed + '\\'))
    throw new Error('Native outputs must stay under output');
  return { ...value, out: destination };
}
export function firstDone(history) {
  const result = {};
  for (const revision of history)
    for (const task of parseTasks(revision.markdown))
      if (task.status === 'done' && !result[task.id]) result[task.id] = revision.date;
  return result;
}
export function historyFor(ref) {
  const revisions = git([
    'log',
    ref,
    '--first-parent',
    '--reverse',
    '--format=%H%x09%cI',
    '--',
    'TASKS.md',
  ])
    .trim()
    .split('\n')
    .filter(Boolean);
  return firstDone(
    revisions.map((line) => {
      const [sha, time] = line.split('\t');
      const date = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Asia/Beirut',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date(time));
      return { date, markdown: git(['show', `${sha}:TASKS.md`]) };
    }),
  );
}
export async function main(args = process.argv.slice(2)) {
  const settings = options(args);
  const source = git(['rev-parse', '--verify', `${settings.ref}^{commit}`]).trim();
  const config = JSON.parse(readFileSync(resolve(root, 'web/project-board.json'), 'utf8'));
  const native = JSON.parse(readFileSync(resolve(root, 'web/project-native-board.json'), 'utf8'));
  const plan = planBoard(git(['show', `${source}:TASKS.md`]), config, source);
  const completed = historyFor(source);
  let project = await nativeSnapshot(github, plan.owner, 4);
  const proposed = planNative(project, plan, native.meeting_dates, completed, {
    allowMissing: true,
  });
  const configuration = configurationChanges(project, native.meeting_dates);
  const document = {
    kind: 'current native-field backlog plan',
    source_commit: source,
    source_ref: settings.ref,
    meeting_dates: native.meeting_dates,
    meeting_dates_source: native.meeting_dates_source,
    allocation_note:
      'Current planning/grouping from repository history; not original meeting assignments or verified minutes',
    configuration_mutations: configuration.length,
    cards: proposed.map(publicRow),
  };
  mkdirSync(dirname(settings.out), { recursive: true });
  writeFileSync(settings.out, JSON.stringify(document, null, 2) + '\n');
  if (!settings.apply) {
    log(
      JSON.stringify(
        {
          mode: 'dry-run',
          source_commit: source,
          cards: proposed.length,
          configuration_mutations: configuration.length,
          output: settings.out,
        },
        null,
        2,
      ),
    );
    return;
  }
  const mirror = await syncBoard(github, plan, 4, { adopt: true });
  project = await nativeSnapshot(github, plan.owner, 4);
  await batch(github, configurationChanges(project, native.meeting_dates));
  project = await nativeSnapshot(github, plan.owner, 4);
  const rows = planNative(project, plan, native.meeting_dates, completed);
  const operations = nativeOperations(project, rows).length;
  await applyNative(github, project, rows, native.meeting_dates);
  const receipt = {
    kind: 'verified native-field backlog reconciliation',
    observed_at_utc: new Date().toISOString(),
    source_commit: source,
    source_ref: settings.ref,
    task_cards: plan.cards.length,
    issue_cards: rows
      .filter((x) => x.kind === 'issue')
      .map((x) => ({ number: x.issue, owner: x.owner, status: x.status })),
    meeting_dates: native.meeting_dates,
    meeting_dates_source: native.meeting_dates_source,
    mirror,
    native_mutations: operations,
    remaining_mutations: 0,
    verified: true,
    allocation_note: document.allocation_note,
    cards: rows.map(publicRow),
  };
  writeFileSync(
    resolve(root, 'output/native-board-receipt.json'),
    JSON.stringify(receipt, null, 2) + '\n',
  );
  log(
    JSON.stringify(
      {
        source_commit: source,
        task_cards: receipt.task_cards,
        issue_cards: receipt.issue_cards,
        meeting_dates: receipt.meeting_dates,
        native_mutations: operations,
        remaining_mutations: 0,
        verified: true,
      },
      null,
      2,
    ),
  );
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href)
  main().catch((e) => {
    error(e.message);
    process.exitCode = 1;
  });
