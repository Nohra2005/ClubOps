/** REST can create vertical column grouping; GraphQL only edits visible view fields. */
import { preflight, snapshot } from './project-github.mjs';
import { assertPreserved, profileFor, resolveFields } from './project-profile.mjs';
export const columnsView = 'ClubOps status columns';

export async function configureColumns(api, rest, plan, number) {
  const project = await snapshot(api, plan.owner, number);
  preflight(project, plan);
  const profile = profileFor(project, plan);
  const fields = resolveFields(project, profile);
  const status = fields.get('Status');
  const existing = project.views.nodes.filter((view) => view.name === columnsView);
  if (existing.length > 1)
    throw new Error('Ambiguous status-column views; inspect before retrying');
  const correct = (view) =>
    view?.layout === 'BOARD_LAYOUT' &&
    view.verticalGroupByFields?.nodes.length === 1 &&
    view.verticalGroupByFields.nodes[0].id === status.id;
  if (existing.length && !correct(existing[0]))
    throw new Error('Existing status-column view differs; refusing to overwrite its settings');
  let created = false;
  if (!existing.length) {
    const rows = await rest(`/users/${plan.owner}/projectsV2/${number}/fields?per_page=100`, 'GET');
    if (!Array.isArray(rows) || rows.length !== project.fields.nodes.length)
      throw new Error('REST field listing is incomplete; no view created');
    const numeric = (nodeId) => {
      const matches = rows.filter((row) => row.node_id === nodeId);
      if (matches.length !== 1 || !Number.isSafeInteger(matches[0].id) || matches[0].id <= 0)
        throw new Error('Unresolved numeric field ID; no view created');
      return matches[0].id;
    };
    const titles = rows.filter((row) => row.data_type === 'title');
    if (titles.length !== 1) throw new Error('Unresolved title field; no view created');
    await rest(`/users/${plan.owner}/projectsV2/${number}/views`, 'POST', {
      name: columnsView,
      layout: 'board',
      visible_fields: [
        numeric(titles[0].node_id),
        ...[...fields.values()].map((field) => numeric(field.id)),
      ],
      vertical_group_by: [numeric(status.id)],
      group_by: [],
    });
    created = true;
  }
  const after = await snapshot(api, plan.owner, number);
  const views = after.views.nodes.filter((view) => view.name === columnsView);
  if (views.length !== 1 || !correct(views[0]))
    throw new Error('Status-column read-back failed; inspect before retrying');
  // Creating a new view must not alter any existing view, field, item, README or visibility.
  assertPreserved(
    { ...project, fields: project.fields.nodes, views: project.views.nodes },
    { ...after, fields: after.fields.nodes, views: after.views.nodes },
  );
  return {
    url: `${project.url}/views/${views[0].number}`,
    name: columnsView,
    column_field: status.name,
    verified: true,
    created,
    previous_views_preserved: true,
  };
}
