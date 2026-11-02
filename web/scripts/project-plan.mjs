/** TASKS.md is the source of truth; this module performs no network or filesystem writes. */
import { createHash } from 'node:crypto';

export const statuses = ['todo', 'doing', 'blocked', 'review', 'done'];
export const owners = ['tatiana', 'christophe', 'joey'];
export const marker = '<!-- clubops-task-board:v1 -->';

export function parseTasks(markdown) {
  const visible = markdown.replace(/<!--[\s\S]*?-->/g, '');
  const sections = [
    ...visible.matchAll(/^### ([TCJ]-\d{2}) (.+)\r?\n([\s\S]*?)(?=^### |^## |$(?![\s\S]))/gm),
  ];
  const tasks = sections.map(([, id, title, body]) => {
    const read = (name) => {
      const matches = [...body.matchAll(new RegExp(`^- ${name}: (.+)$`, 'gm'))];
      if (matches.length !== 1) throw new Error(`${id}: expected one ${name} field`);
      return matches[0][1].trim();
    };
    const owner = read('Owner');
    const status = read('Status');
    const needs = read('Needs');
    if (!owners.includes(owner) || !statuses.includes(status))
      throw new Error(`${id}: invalid owner/status`);
    return {
      id,
      title: title.trim(),
      owner,
      status,
      needs: needs === 'none' ? [] : needs.split(',').map((s) => s.trim()),
      body: body.trim(),
    };
  });
  if (!tasks.length) throw new Error('No tasks found');
  const ids = new Set(tasks.map((task) => task.id));
  if (ids.size !== tasks.length) throw new Error('Duplicate task id');
  for (const task of tasks)
    if (task.needs.some((need) => !ids.has(need)))
      throw new Error(`${task.id}: unknown dependency`);
  return tasks;
}

export function planBoard(markdown, config, ref) {
  if (
    !/^[a-zA-Z0-9-]+\/[a-zA-Z0-9_.-]+$/.test(config.repository) ||
    !/^[a-zA-Z0-9-]+$/.test(config.owner)
  )
    throw new Error('Invalid GitHub repository/owner');
  if (!/^[a-f0-9]{40}$/.test(ref)) throw new Error('Use an exact source commit SHA');
  if (typeof config.title !== 'string' || !config.title.trim() || config.title.length > 120)
    throw new Error('Invalid project title');
  const tasks = parseTasks(markdown);
  const ids = new Set(tasks.map((task) => task.id));
  const assignments = new Map();
  const titles = new Set();
  let previousEnd = 0;
  if (!Array.isArray(config.sprints) || config.sprints.length < 3)
    throw new Error('Plan at least three weekly sprints');
  const sprints = config.sprints.map((sprint) => {
    const start = Date.parse(`${sprint.startDate}T00:00:00Z`);
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(sprint.startDate) ||
      !Number.isFinite(start) ||
      new Date(start).toISOString().slice(0, 10) !== sprint.startDate ||
      sprint.duration !== 7 ||
      start < previousEnd
    )
      throw new Error('Sprints must be valid, ordered, non-overlapping seven-day periods');
    if (typeof sprint.title !== 'string' || !sprint.title.trim() || titles.has(sprint.title))
      throw new Error('Sprint titles must be unique');
    titles.add(sprint.title);
    previousEnd = start + 7 * 86400000;
    if (!Array.isArray(sprint.tasks)) throw new Error('Sprint tasks must be a list');
    for (const id of sprint.tasks) {
      if (!ids.has(id) || assignments.has(id))
        throw new Error(`Unknown or repeated sprint task: ${id}`);
      assignments.set(id, sprint.title);
    }
    return { title: sprint.title, startDate: sprint.startDate, duration: 7 };
  });
  const source = `https://github.com/${config.repository}/blob/${ref}/TASKS.md`;
  return {
    schema: 1,
    repository: config.repository,
    owner: config.owner,
    title: config.title,
    source: {
      url: source,
      commit: ref,
      sha256: createHash('sha256').update(markdown).digest('hex'),
    },
    statuses,
    owners,
    sprints,
    cards: tasks.map((task) => ({
      ...task,
      title: `${task.id}: ${task.title}`,
      body: `${marker}\nTask: ${task.id}\n\nSource: ${source}\n\n${task.body}\n\nThis card mirrors TASKS.md. Change the task there, then sync. Sprint assignments are tentative plans, not completed reviews.`,
      sprint: assignments.get(task.id) ?? null,
    })),
  };
}

export function managedItems(items) {
  const result = new Map();
  for (const item of items) {
    if (!item.content?.body?.startsWith(`${marker}\nTask: `)) continue;
    const id = /^Task: ([TCJ]-\d{2})$/m.exec(item.content.body)?.[1];
    if (!id || result.has(id))
      throw new Error('Duplicate or malformed managed task card; no mutations applied');
    if (item.content.__typename !== 'DraftIssue' || item.isArchived)
      throw new Error(`${id}: restore the managed draft card before syncing`);
    result.set(id, item);
  }
  return result;
}
