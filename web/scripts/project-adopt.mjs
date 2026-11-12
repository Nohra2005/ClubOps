/** Explicit additive adoption. Never rename/reconfigure a human field or replace README text. */
import { batch, inspectProject, operation, snapshot } from './project-github.mjs';
import { validateConfiguration } from './project-fields.mjs';
import { columnsView } from './project-columns.mjs';
import {
  additive,
  adoptionBlock,
  profileFor,
  preserveUnmanaged,
  assertPreserved,
} from './project-profile.mjs';

export function inspectAdoption(project, plan, number) {
  if (
    project.title !== plan.title ||
    project.url !== `https://github.com/users/${plan.owner}/projects/${number}`
  )
    throw new Error('Adoption target owner/number/title does not match the pinned plan');
  const managed = inspectProject(project, plan);
  const profile = profileFor(project, plan);
  if (profile && profile.kind !== 'additive')
    throw new Error('This is already a dedicated board; use normal sync');
  if (
    !profile &&
    (project.fields.nodes.some((field) => Object.values(additive.fields).includes(field.name)) ||
      project.views.nodes.some((view) => [additive.view, columnsView].includes(view.name)))
  )
    throw new Error(
      'An unmarked board already uses the reserved ClubOps namespace; inspect before adoption',
    );
  // All configuration/identity validation precedes even the ownership-marker append.
  validateConfiguration(project, plan, additive);
  return {
    url: project.url,
    project_id: project.id,
    adoption_needed: !profile,
    existing_managed_tasks: managed.size,
    manual_items: project.items.length - managed.size,
    field_names: additive.fields,
    view: additive.view,
    view_grouping: 'Set and verify ClubOps status in the GitHub UI; API cannot configure grouping',
  };
}

export async function adoptProject(api, project, plan, number) {
  const report = inspectAdoption(project, plan, number);
  if (!report.adoption_needed) return project;
  const readme = `${project.readme ?? ''}\n\n${adoptionBlock(project, plan)}\n\n### ClubOps task mirror\nTASKS.md is authoritative for marked task drafts and the ClubOps fields/view only. Existing issue cards, Status and Iteration remain manual. Sprint assignments are proposals, not evidence of completed weekly reviews.\n`;
  const before = preserveUnmanaged({ ...project, readme }, additive);
  await batch(api, [
    operation(
      'updateProjectV2',
      'UpdateProjectV2Input',
      {
        projectId: project.id,
        readme,
      },
      'projectV2 { id }',
    ),
  ]);
  const verified = await snapshot(api, plan.owner, number);
  if (profileFor(verified, plan)?.kind !== 'additive')
    throw new Error('Adoption marker read-back failed; inspect before retrying');
  assertPreserved(before, preserveUnmanaged(verified, additive));
  return verified;
}
