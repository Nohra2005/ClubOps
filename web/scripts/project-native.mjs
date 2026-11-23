/** Native GitHub adapter and verified reconciliation. */
import { batch, operation, snapshot } from './project-github.mjs';
import {
  configurationChanges,
  field,
  iterations,
  nativeDescription,
  nativeNote,
} from './project-native-plan.mjs';
export {
  configurationChanges,
  mondayWeeks,
  ownerLogins,
  planNative,
} from './project-native-plan.mjs';

export async function nativeSnapshot(api, owner, number) {
  const project = await snapshot(api, owner, number);
  const details = [];
  let cursor = null;
  const seen = new Set();
  let users;
  do {
    const data = await api(
      `query NativeDetails($id:ID!,$cursor:String){
      node(id:$id){...on ProjectV2{
        fields(first:100){nodes{...on ProjectV2SingleSelectField{id name options{id name color description}}}}
        items(first:100,after:$cursor){pageInfo{hasNextPage endCursor} nodes{id content{
          __typename ...on DraftIssue{id assignees(first:20){nodes{id login} pageInfo{hasNextPage}}}
          ...on Issue{id number state url repository{nameWithOwner} assignees(first:20){nodes{id login} pageInfo{hasNextPage}}}
        }}}
      }}
      tatiana:user(login:"Nohra2005"){id login} christophe:user(login:"chrs-005"){id login} joey:user(login:"JS9872"){id login}
    }`,
      { id: project.id, cursor },
    );
    const page = data.node?.items;
    if (!page || !Array.isArray(page.nodes)) throw new Error('Missing native item page');
    details.push(...page.nodes);
    users = { tatiana: data.tatiana, christophe: data.christophe, joey: data.joey };
    for (const field of data.node.fields.nodes.filter((x) => x.id)) {
      const current = project.fields.nodes.find((x) => x.id === field.id);
      if (current) current.options = field.options;
    }
    const next = page.pageInfo.hasNextPage ? page.pageInfo.endCursor : null;
    if (page.pageInfo.hasNextPage && (!next || next === cursor || seen.has(next)))
      throw new Error('Incomplete native pagination');
    if (next) seen.add(next);
    cursor = next;
  } while (cursor);
  const byId = new Map(details.map((x) => [x.id, x]));
  if (byId.size !== project.items.length) throw new Error('Board changed during inventory');
  project.items = project.items.map((item) => {
    const detail = byId.get(item.id);
    if (!detail || detail.content?.assignees?.pageInfo?.hasNextPage)
      throw new Error('Incomplete native assignment inventory');
    return { ...item, content: { ...item.content, ...detail.content } };
  });
  return { ...project, users };
}

export function nativeOperations(project, rows) {
  const result = [];
  for (const row of rows) {
    const item = project.items.find((x) => x.id === row.item_id);
    if (!item) throw new Error('Missing native target');
    const assigned = item.content.assignees.nodes.map((x) => x.id);
    if (row.kind === 'task' && (assigned.length !== 1 || assigned[0] !== row.assignee_id))
      result.push(
        operation(
          'updateProjectV2DraftIssue',
          'UpdateProjectV2DraftIssueInput',
          { draftIssueId: row.content_id, assigneeIds: [row.assignee_id] },
          'draftIssue { id }',
        ),
      );
    if (row.kind === 'issue' && !assigned.includes(row.assignee_id))
      result.push(
        operation(
          'addAssigneesToAssignable',
          'AddAssigneesToAssignableInput',
          { assignableId: row.content_id, assigneeIds: [row.assignee_id] },
          'assignable { ...on Issue { id } }',
        ),
      );
    const values = new Map(
      item.fieldValues.nodes.filter((x) => x.field).map((x) => [x.field.id, x]),
    );
    const desired = {
      Status: {
        singleSelectOptionId: field(project, 'Status', 'SINGLE_SELECT').options.find(
          (x) => x.name === row.status,
        )?.id,
      },
      Priority: {
        singleSelectOptionId: field(project, 'Priority', 'SINGLE_SELECT').options.find(
          (x) => x.name === row.priority,
        )?.id,
      },
      Size: {
        singleSelectOptionId: field(project, 'Size', 'SINGLE_SELECT').options.find(
          (x) => x.name === row.size,
        )?.id,
      },
      Estimate: { number: row.estimate },
      Iteration: row.iteration_start
        ? {
            iterationId: iterations(field(project, 'Iteration', 'ITERATION')).find(
              (x) => x.startDate === row.iteration_start,
            )?.id,
          }
        : null,
    };
    if (row.kind === 'issue') {
      desired['ClubOps status'] = {
        singleSelectOptionId: field(project, 'ClubOps status', 'SINGLE_SELECT').options.find(
          (x) => x.name === row.task_status,
        )?.id,
      };
      desired['ClubOps owner'] = {
        singleSelectOptionId: field(project, 'ClubOps owner', 'SINGLE_SELECT').options.find(
          (x) => x.name === row.owner,
        )?.id,
      };
    }
    for (const [name, value] of Object.entries(desired)) {
      const f = project.fields.nodes.find((x) => x.name === name);
      const before = values.get(f.id);
      if (value && Object.values(value).some((x) => x === undefined))
        throw new Error('Unresolved native field value');
      const key = value ? Object.keys(value)[0] : null;
      const actual =
        key === 'singleSelectOptionId'
          ? before?.optionId
          : key === 'iterationId'
            ? before?.iterationId
            : before?.number;
      if ((value && actual === value[key]) || (!value && !before)) continue;
      const input = { projectId: project.id, itemId: item.id, fieldId: f.id };
      result.push(
        value
          ? operation(
              'updateProjectV2ItemFieldValue',
              'UpdateProjectV2ItemFieldValueInput',
              { ...input, value },
              'projectV2Item { id }',
            )
          : operation(
              'clearProjectV2ItemFieldValue',
              'ClearProjectV2ItemFieldValueInput',
              input,
              'projectV2Item { id }',
            ),
      );
    }
  }
  if (!project.readme?.includes(nativeNote))
    result.push(
      operation(
        'updateProjectV2',
        'UpdateProjectV2Input',
        { projectId: project.id, readme: `${project.readme ?? ''}\n\n${nativeDescription}\n` },
        'projectV2 { id }',
      ),
    );
  return result;
}

export async function applyNative(api, project, rows, dates) {
  await batch(api, nativeOperations(project, rows));
  const after = await nativeSnapshot(api, 'Nohra2005', 4);
  if (configurationChanges(after, dates).length || nativeOperations(after, rows).length)
    throw new Error('Native read-back differs; inspect before resuming');
  const content = new Map(after.items.map((x) => [x.id, x.content]));
  for (const item of project.items) {
    const value = content.get(item.id);
    if (!value || value.title !== item.content.title || value.body !== item.content.body)
      throw new Error('Card content changed during native update');
  }
  if (
    after.items.length !== project.items.length ||
    after.public ||
    JSON.stringify(after.views) !== JSON.stringify(project.views)
  )
    throw new Error('Board structure changed unexpectedly');
  return after;
}
