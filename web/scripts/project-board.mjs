/** C-31 CLI: dry-run by default; authenticated writes need --apply explicitly. */
import { spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import process from 'node:process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { log, error } from 'node:console';
import { planBoard } from './project-plan.mjs';
import { createBoard, snapshot } from './project-github.mjs';
import { syncBoard } from './project-sync.mjs';
import { inspectAdoption } from './project-adopt.mjs';
import { publicFailure } from './project-errors.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

function command(program, args, input) {
  const environment = { ...process.env };
  delete environment.GH_DEBUG;
  const result = spawnSync(program, args, {
    cwd: root,
    encoding: 'utf8',
    input,
    maxBuffer: 16 * 1024 * 1024,
    env: environment,
  });
  if (result.error)
    throw new Error(`${program} could not start; check the documented prerequisites`);
  return result;
}

export async function github(query, variables) {
  const result = command(
    process.platform === 'win32' ? 'gh.exe' : 'gh',
    ['api', 'graphql', '--input', '-'],
    JSON.stringify({ query, variables }),
  );
  let response;
  try {
    response = JSON.parse(result.stdout);
  } catch {
    response = null;
  }
  if (result.status !== 0 || response?.errors?.length || !response?.data)
    throw publicFailure(result, response);
  return response.data;
}

export function options(args) {
  const result = {
    apply: false,
    create: false,
    adopt: false,
    ref: 'origin/main',
    config: 'web/project-board.json',
    out: 'output/project-board-plan.json',
    number: null,
  };
  for (let index = 0; index < args.length; index++) {
    const argument = args[index];
    if (argument === '--apply') result.apply = true;
    else if (argument === '--create') result.create = true;
    else if (argument === '--adopt') result.adopt = true;
    else if (['--ref', '--config', '--out', '--project-number'].includes(argument)) {
      const value = args[++index];
      if (!value || value.startsWith('--')) throw new Error(`${argument} needs a value`);
      if (argument === '--project-number') {
        if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(Number(value)))
          throw new Error('Invalid project number');
        result.number = Number(value);
      } else result[argument.slice(2)] = value;
    } else throw new Error(`Unknown option: ${argument}`);
  }
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_./-]*$/.test(result.ref)) throw new Error('Invalid source ref');
  if (result.create && !result.apply) throw new Error('--create also requires --apply');
  if (result.apply && !result.create && result.number === null)
    throw new Error('--apply needs --project-number or --create');
  if (result.create && result.number !== null)
    throw new Error('Choose --create or --project-number, not both');
  if (result.adopt && (result.create || result.number === null))
    throw new Error('--adopt requires an existing --project-number and cannot create a board');
  return result;
}

export async function main(args = process.argv.slice(2)) {
  const settings = options(args);
  const commit = command('git', ['rev-parse', '--verify', `${settings.ref}^{commit}`]);
  if (commit.status !== 0) throw new Error('Source ref not found. Fetch origin/main first.');
  const sha = commit.stdout.trim();
  const source = command('git', ['show', `${sha}:TASKS.md`]);
  if (source.status !== 0) throw new Error('TASKS.md is missing from that commit');
  const config = JSON.parse(readFileSync(resolve(root, settings.config), 'utf8'));
  const plan = planBoard(source.stdout, config, sha);
  const destination = resolve(root, settings.out);
  if (
    !destination.startsWith(`${resolve(root, 'output')}/`) &&
    !destination.startsWith(`${resolve(root, 'output')}\\`)
  )
    throw new Error('Plan outputs must stay under output/ so source files cannot be overwritten');
  mkdirSync(dirname(destination), { recursive: true });
  const adoption =
    settings.adopt && !settings.apply
      ? inspectAdoption(await snapshot(github, plan.owner, settings.number), plan, settings.number)
      : undefined;
  writeFileSync(
    destination,
    `${JSON.stringify({ ...plan, ...(adoption ? { adoption } : {}) }, null, 2)}\n`,
  );
  if (!settings.apply) {
    log(
      JSON.stringify(
        {
          mode: 'dry-run',
          tasks: plan.cards.length,
          source_commit: sha,
          output: destination,
          sprints: plan.sprints.map((sprint) => sprint.title),
          published: false,
          ...(adoption ? { adoption } : {}),
        },
        null,
        2,
      ),
    );
    return;
  }
  const number = settings.create ? await createBoard(github, plan) : settings.number;
  const result = await syncBoard(github, plan, number, { adopt: settings.adopt });
  writeFileSync(
    resolve(root, 'output/project-board-sync.json'),
    `${JSON.stringify(result, null, 2)}\n`,
  );
  log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch((failure) => {
    error(failure.message);
    process.exitCode = 1;
  });
}
