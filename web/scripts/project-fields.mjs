/** Managed project fields: preserve existing identities and reject conflicting configuration. */
import { batch, fieldSelection, operation } from './project-github.mjs';

export async function configure(api, project, plan) {
  const fields = new Map(project.fields.nodes.map((field) => [field.name, field]));
  const definitions = [
    { name: 'Status', dataType: 'SINGLE_SELECT', options: plan.statuses },
    { name: 'Owner', dataType: 'SINGLE_SELECT', options: plan.owners },
    { name: 'Task ID', dataType: 'TEXT' },
    { name: 'Needs', dataType: 'TEXT' },
    { name: 'Sprint', dataType: 'ITERATION' },
  ];
  // Validate every existing field before applying any configuration changes.
  for (const definition of definitions) {
    const field = fields.get(definition.name);
    if (!field) continue;
    if (field.dataType !== definition.dataType)
      throw new Error(`${field.name}: incompatible field type`);
    if (
      definition.options &&
      JSON.stringify(field.options.map((option) => option.name)) !==
        JSON.stringify(definition.options)
    ) {
      const emptyDefaultStatus =
        field.name === 'Status' &&
        project.items.length === 0 &&
        field.options.every((option) => ['Todo', 'In Progress', 'Done'].includes(option.name));
      if (!emptyDefaultStatus)
        throw new Error(`${field.name}: options differ; refusing to reset live assignments`);
    }
    if (field.name === 'Sprint') {
      const existing = [
        ...field.configuration.completedIterations,
        ...field.configuration.iterations,
      ];
      for (const desired of plan.sprints) {
        const same = existing.filter((iteration) => iteration.title === desired.title);
        if (
          same.length > 1 ||
          same.some(
            (iteration) =>
              iteration.startDate !== desired.startDate || iteration.duration !== desired.duration,
          )
        )
          throw new Error(
            'Sprint dates changed; preserve existing iteration identities and reconcile manually',
          );
      }
    }
  }
  const colors = ['GRAY', 'BLUE', 'RED', 'YELLOW', 'GREEN'];
  for (const definition of definitions) {
    let field = fields.get(definition.name);
    const options = definition.options?.map((name, index) => ({
      name,
      description: name,
      color: colors[index],
    }));
    if (!field) {
      const input = { projectId: project.id, name: definition.name, dataType: definition.dataType };
      if (options) input.singleSelectOptions = options;
      if (definition.name === 'Sprint')
        input.iterationConfiguration = {
          startDate: plan.sprints[0].startDate,
          duration: 7,
          iterations: plan.sprints,
        };
      const [result] = await batch(api, [
        operation(
          'createProjectV2Field',
          'CreateProjectV2FieldInput',
          input,
          `projectV2Field { ${fieldSelection} }`,
        ),
      ]);
      field = result.projectV2Field;
      fields.set(definition.name, field);
    } else if (
      options &&
      JSON.stringify(field.options.map((option) => option.name)) !==
        JSON.stringify(definition.options)
    ) {
      const [result] = await batch(api, [
        operation(
          'updateProjectV2Field',
          'UpdateProjectV2FieldInput',
          {
            fieldId: field.id,
            singleSelectOptions: options,
          },
          `projectV2Field { ${fieldSelection} }`,
        ),
      ]);
      field = result.projectV2Field;
      fields.set(definition.name, field);
    }
    if (definition.name === 'Sprint') {
      const existing = [
        ...field.configuration.completedIterations,
        ...field.configuration.iterations,
      ];
      const missing = plan.sprints.filter(
        (desired) => !existing.some((iteration) => iteration.title === desired.title),
      );
      if (missing.length) {
        const iterations = [...existing, ...missing].sort((a, b) =>
          a.startDate.localeCompare(b.startDate),
        );
        const [result] = await batch(api, [
          operation(
            'updateProjectV2Field',
            'UpdateProjectV2FieldInput',
            {
              fieldId: field.id,
              iterationConfiguration: {
                startDate: iterations[0].startDate,
                duration: 7,
                iterations,
              },
            },
            `projectV2Field { ${fieldSelection} }`,
          ),
        ]);
        fields.set(definition.name, result.projectV2Field);
      }
    }
  }
  const view = project.views.nodes.find((candidate) => candidate.name === 'Tasks by status');
  const configuration = {
    visibleFieldIds: ['Status', 'Owner', 'Task ID', 'Needs', 'Sprint'].map(
      (name) => fields.get(name).id,
    ),
  };
  if (!view)
    await batch(api, [
      operation(
        'createProjectV2View',
        'CreateProjectV2ViewInput',
        {
          projectId: project.id,
          name: 'Tasks by status',
          layout: 'BOARD_LAYOUT',
          configuration,
        },
        'projectV2View { id }',
      ),
    ]);
  else if (view.layout !== 'BOARD_LAYOUT')
    throw new Error('Managed board view layout changed; reconcile manually');
  return fields;
}

function desiredValues(card, fields) {
  const single = (field, name) => {
    const option = fields.get(field).options.find((candidate) => candidate.name === name);
    if (!option) throw new Error(`${field}: required option missing`);
    return { singleSelectOptionId: option.id };
  };
  const sprint = fields.get('Sprint');
  const iterations = [
    ...sprint.configuration.iterations,
    ...sprint.configuration.completedIterations,
  ];
  return {
    Status: single('Status', card.status),
    Owner: single('Owner', card.owner),
    'Task ID': { text: card.id },
    Needs: { text: card.needs.join(', ') || 'none' },
    Sprint: card.sprint
      ? { iterationId: iterations.find((iteration) => iteration.title === card.sprint)?.id }
      : null,
  };
}

export function changes(projectId, card, item, fields) {
  const operations = [];
  if (item.content.title !== card.title || item.content.body !== card.body)
    operations.push(
      operation(
        'updateProjectV2DraftIssue',
        'UpdateProjectV2DraftIssueInput',
        {
          draftIssueId: item.content.id,
          title: card.title,
          body: card.body,
        },
        'draftIssue { id }',
      ),
    );
  const current = new Map(
    (item.fieldValues?.nodes ?? [])
      .filter((value) => value.field)
      .map((value) => [
        value.field.id,
        value.text !== undefined
          ? { text: value.text }
          : value.optionId !== undefined
            ? { singleSelectOptionId: value.optionId }
            : { iterationId: value.iterationId },
      ]),
  );
  for (const [name, value] of Object.entries(desiredValues(card, fields))) {
    const fieldId = fields.get(name).id;
    const before = current.get(fieldId) ?? null;
    if (JSON.stringify(before) === JSON.stringify(value)) continue;
    const input = { projectId, itemId: item.id, fieldId };
    if (value !== null) {
      if (Object.values(value).some((entry) => !entry))
        throw new Error(`${name}: unresolved field value`);
      input.value = value;
      operations.push(
        operation(
          'updateProjectV2ItemFieldValue',
          'UpdateProjectV2ItemFieldValueInput',
          input,
          'projectV2Item { id }',
        ),
      );
    } else
      operations.push(
        operation(
          'clearProjectV2ItemFieldValue',
          'ClearProjectV2ItemFieldValueInput',
          input,
          'projectV2Item { id }',
        ),
      );
  }
  return operations;
}
