/** GitHub Projects v2 adapter. No deletes, public exposure, tokens or workflow credentials. */
import { managedItems, marker } from './project-plan.mjs';
import { profileFor } from './project-profile.mjs';

export const fieldSelection = `
 ... on ProjectV2Field { id name dataType }
 ... on ProjectV2SingleSelectField { id name dataType options { id name } }
 ... on ProjectV2IterationField { id name dataType configuration {
   iterations { id title startDate duration } completedIterations { id title startDate duration }
 } }`;
export const itemSelection = `id isArchived content {
 __typename ... on DraftIssue { id title body } ... on Issue { title body } ... on PullRequest { title body }
} fieldValues(first:20) { pageInfo { hasNextPage } nodes {
 ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2Field { id } } }
 ... on ProjectV2ItemFieldSingleSelectValue { optionId field { ... on ProjectV2SingleSelectField { id } } }
 ... on ProjectV2ItemFieldIterationValue { iterationId field { ... on ProjectV2IterationField { id } } }
} }`;

async function pages(api, query, variables, connection) {
  const nodes = [];
  const visited = new Set();
  let cursor = null;
  do {
    const page = connection(await api(query, { ...variables, cursor }));
    if (!page || !Array.isArray(page.nodes)) throw new Error('Missing Projects connection');
    nodes.push(...page.nodes);
    const next = page.pageInfo.hasNextPage ? page.pageInfo.endCursor : null;
    if (page.pageInfo.hasNextPage && (!next || next === cursor || visited.has(next)))
      throw new Error('Invalid Projects pagination');
    visited.add(next);
    cursor = next;
  } while (cursor);
  return nodes;
}

export async function batch(api, operations) {
  const results = [];
  for (let start = 0; start < operations.length; start += 20) {
    const group = operations.slice(start, start + 20);
    const variables = Object.fromEntries(group.map((op, i) => [`i${i}`, op.input]));
    const declarations = group.map((op, i) => `$i${i}:${op.type}!`).join(',');
    const body = group.map((op, i) => `m${i}:${op.name}(input:$i${i}){${op.selection}}`).join('\n');
    const data = await api(`mutation BoardWrite(${declarations}) { ${body} }`, variables);
    results.push(...group.map((_, i) => data[`m${i}`]));
  }
  return results;
}

export const operation = (name, type, input, selection) => ({ name, type, input, selection });

export async function createBoard(api, plan) {
  const [repoOwner, repoName] = plan.repository.split('/');
  const identity = await api(
    `query Identity($owner:String!,$repoOwner:String!,$repoName:String!) {
      viewer { id login } user(login:$owner) { id }
      repository(owner:$repoOwner,name:$repoName) { id nameWithOwner }
    }`,
    { owner: plan.owner, repoOwner, repoName },
  );
  if (identity.viewer.login.toLowerCase() !== plan.owner.toLowerCase())
    throw new Error(
      'Create the board under the authenticated owner, or supply an existing project number',
    );
  if (
    !identity.repository ||
    identity.repository.nameWithOwner.toLowerCase() !== plan.repository.toLowerCase()
  )
    throw new Error('Repository is unavailable');
  const existing = await pages(
    api,
    `query ExistingBoards($owner:String!,$cursor:String) { user(login:$owner) {
      projectsV2(first:100,after:$cursor) { nodes { number title readme } pageInfo { hasNextPage endCursor } }
    } }`,
    { owner: plan.owner },
    (data) => data.user?.projectsV2,
  );
  const matches = existing.filter((project) => project.title === plan.title);
  if (
    matches.length > 1 ||
    (matches.length === 1 && !matches[0].readme?.startsWith(`${marker}\n${plan.repository}\n`))
  )
    throw new Error('An ambiguous or unmanaged project has this title; no duplicate board created');
  if (matches.length === 1) return matches[0].number;
  const [created] = await batch(api, [
    operation(
      'createProjectV2',
      'CreateProjectV2Input',
      {
        ownerId: identity.user.id,
        title: plan.title,
        repositoryId: identity.repository.id,
      },
      'projectV2 { id number url }',
    ),
  ]);
  const project = created.projectV2;
  await batch(api, [
    operation(
      'updateProjectV2',
      'UpdateProjectV2Input',
      {
        projectId: project.id,
        public: false,
        readme: `${marker}\n${plan.repository}\n\nTASKS.md is authoritative. Status/Owner/Task ID/Needs/Sprint are managed by web/scripts/project-board.mjs. Sprints are tentative plans; completed team reviews are recorded separately. No real club data belongs here.`,
        shortDescription: 'TASKS.md mirror and proposed weekly sprints. No completed-review claim.',
      },
      'projectV2 { id }',
    ),
  ]);
  return project.number;
}

export async function snapshot(api, owner, number) {
  const data = await api(
    `query Board($owner:String!,$number:Int!) { user(login:$owner) { projectV2(number:$number) {
      id title url public closed readme viewerCanUpdate
      fields(first:100) { nodes { ${fieldSelection} } pageInfo { hasNextPage } }
      views(first:100) { nodes { id name layout } pageInfo { hasNextPage } }
    } } }`,
    { owner, number },
  );
  const project = data.user?.projectV2;
  if (!project) throw new Error('Project not found');
  if (project.fields.pageInfo.hasNextPage || project.views.pageInfo.hasNextPage)
    throw new Error('Unexpectedly large project configuration; refusing a partial sync');
  const items = await pages(
    api,
    `query BoardItems($id:ID!,$cursor:String) { node(id:$id) { ... on ProjectV2 {
      items(first:100,after:$cursor) { nodes { ${itemSelection} } pageInfo { hasNextPage endCursor } }
    } } }`,
    { id: project.id },
    (value) => value.node?.items,
  );
  return { ...project, items };
}

export function inspectProject(project, plan) {
  if (project.public || project.closed || !project.viewerCanUpdate)
    throw new Error('Sync requires an open, private project with write access');
  const managed = managedItems(project.items);
  const ids = new Set(plan.cards.map((card) => card.id));
  for (const id of managed.keys())
    if (!ids.has(id))
      throw new Error(
        `Managed card ${id} is no longer in TASKS.md; reconcile it without deleting history`,
      );
  for (const item of project.items) {
    if (item.fieldValues?.pageInfo.hasNextPage)
      throw new Error('Too many item fields; refusing partial comparison');
    const id = /^([TCJ]-\d{2}): /.exec(item.content?.title ?? '')?.[1];
    if (ids.has(id) && managed.get(id)?.id !== item.id)
      throw new Error(`${id}: unmanaged or duplicate task card; reconcile it before syncing`);
  }
  const names = project.fields.nodes.map((field) => field.name);
  if (new Set(names).size !== names.length) throw new Error('Duplicate project field names');
  return managed;
}

export function preflight(project, plan) {
  if (!profileFor(project, plan))
    throw new Error(
      'This is not the dedicated managed ClubOps project; explicit adoption is required',
    );
  return inspectProject(project, plan);
}
