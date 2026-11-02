/** Reconcile task cards, then read every page back before claiming success. */
import { batch, itemSelection, operation, preflight, snapshot } from './project-github.mjs';
import { changes, configure } from './project-fields.mjs';

export async function syncBoard(api, plan, number) {
  const project = await snapshot(api, plan.owner, number);
  let managed = preflight(project, plan);
  const fields = await configure(api, project, plan);
  const missing = plan.cards.filter((card) => !managed.has(card.id));
  const added = await batch(
    api,
    missing.map((card) =>
      operation(
        'addProjectV2DraftIssue',
        'AddProjectV2DraftIssueInput',
        {
          projectId: project.id,
          title: card.title,
          body: card.body,
        },
        `projectItem { ${itemSelection} }`,
      ),
    ),
  );
  missing.forEach((card, index) => managed.set(card.id, added[index].projectItem));
  const operations = plan.cards.flatMap((card) =>
    changes(project.id, card, managed.get(card.id), fields),
  );
  await batch(api, operations);
  const verified = await snapshot(api, plan.owner, number);
  managed = preflight(verified, plan);
  const verifiedFields = new Map(verified.fields.nodes.map((field) => [field.name, field]));
  if (
    managed.size !== plan.cards.length ||
    plan.cards.some(
      (card) =>
        !managed.has(card.id) ||
        changes(project.id, card, managed.get(card.id), verifiedFields).length,
    )
  )
    throw new Error(
      'Read-back did not match TASKS.md; rerun sync to reconcile without duplicating cards',
    );
  return {
    url: project.url,
    tasks: plan.cards.length,
    created: missing.length,
    updates: operations.length,
    source_commit: plan.source.commit,
    verified: true,
  };
}
