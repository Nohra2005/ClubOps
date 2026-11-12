/** Dedicated and additive layouts never share ownership of a human-created field. */
import { marker } from './project-plan.mjs';

const keys = ['Status', 'Owner', 'Task ID', 'Needs', 'Sprint'];
export const dedicated = {
  kind: 'dedicated',
  fields: Object.fromEntries(keys.map((key) => [key, key])),
  view: 'Tasks by status',
};
export const additive = {
  kind: 'additive',
  fields: Object.fromEntries(keys.map((key) => [key, `ClubOps ${key.toLowerCase()}`])),
  view: 'ClubOps tasks by status',
};
export const adoptionMarker = '<!-- clubops-task-board:adopted:v1 -->';
export function adoptionBlock(project, plan) {
  return `${adoptionMarker}\nRepository: ${plan.repository}\nProject: ${project.id}\n<!-- /clubops-task-board:adopted:v1 -->`;
}
export function profileFor(project, plan) {
  const readme = project.readme ?? '';
  const legacy = readme.startsWith(`${marker}\n${plan.repository}\n`);
  if (readme.includes(adoptionMarker)) {
    const block = adoptionBlock(project, plan);
    if (
      legacy ||
      readme.split(adoptionMarker).length !== 2 ||
      !(
        readme === block ||
        readme.startsWith(`${block}\n\n`) ||
        readme.endsWith(`\n\n${block}`) ||
        readme.includes(`\n\n${block}\n\n`)
      )
    )
      throw new Error('Ambiguous or mismatched adoption marker; refusing to claim board ownership');
    return additive;
  }
  return legacy ? dedicated : null;
}

export function fieldDefinitions(plan, profile) {
  return [
    { key: 'Status', dataType: 'SINGLE_SELECT', options: plan.statuses },
    { key: 'Owner', dataType: 'SINGLE_SELECT', options: plan.owners },
    { key: 'Task ID', dataType: 'TEXT' },
    { key: 'Needs', dataType: 'TEXT' },
    { key: 'Sprint', dataType: 'ITERATION' },
  ].map((definition) => ({ ...definition, name: profile.fields[definition.key] }));
}
export function resolveFields(project, profile) {
  return new Map(
    Object.entries(profile.fields).flatMap(([key, name]) => {
      const field = project.fields.nodes.find((candidate) => candidate.name === name);
      return field ? [[key, field]] : [];
    }),
  );
}

// Compare only the previously existing unrelated objects, permitting additive new objects.
const canonical = (value) =>
  JSON.stringify(value, (_, item) =>
    item && typeof item === 'object' && !Array.isArray(item)
      ? Object.fromEntries(
          Object.keys(item)
            .sort()
            .map((key) => [key, item[key]]),
        )
      : item,
  );
export function preserveUnmanaged(project, profile) {
  const managedNames = new Set(Object.values(profile.fields));
  return {
    readme: project.readme,
    public: project.public,
    fields: project.fields.nodes.filter((field) => !managedNames.has(field.name)),
    views: project.views.nodes.filter((view) => view.name !== profile.view),
    items: project.items.filter((item) => !item.content?.body?.startsWith(`${marker}\nTask: `)),
  };
}
export function assertPreserved(before, after) {
  if (before.readme !== after.readme || before.public !== after.public)
    throw new Error('Board description/visibility changed during sync; inspect before retrying');
  for (const key of ['fields', 'views', 'items']) {
    const candidates = new Map(after[key].map((item) => [item.id, item]));
    for (const item of before[key]) {
      if (canonical(candidates.get(item.id)) !== canonical(item))
        throw new Error(
          `An existing manual ${key} entry changed during sync; inspect before retrying`,
        );
    }
  }
}
