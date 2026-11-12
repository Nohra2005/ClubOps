/** Managed project fields: preserve existing identities and reject conflicting configuration. */
import { batch, fieldSelection, operation } from './project-github.mjs';
import { dedicated, fieldDefinitions, resolveFields } from './project-profile.mjs';

export function validateConfiguration(project, plan, profile = dedicated) {
  const fields = resolveFields(project, profile);
  const definitions = fieldDefinitions(plan, profile);
  // Validate every existing field before applying any configuration changes.
  for (const definition of definitions) {
    const field = fields.get(definition.key);
    if (!field) continue;
    if (field.dataType !== definition.dataType)
      throw new Error(`${field.name}: incompatible field type`);
    if (
      definition.options &&
      JSON.stringify(field.options.map((option) => option.name)) !==
        JSON.stringify(definition.options)
    ) {
      const emptyDefaultStatus =
        profile.kind === 'dedicated' &&
        definition.key === 'Status' &&
        project.items.length === 0 &&
        field.options.every((option) => ['Todo', 'In Progress', 'Done'].includes(option.name));
      if (!emptyDefaultStatus)
        throw new Error(`${field.name}: options differ; refusing to reset live assignments`);
    }
    if (definition.key === 'Sprint') {
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
  const views = project.views.nodes.filter((view) => view.name === profile.view);
  if (views.length > 1 || views.some((view) => view.layout !== 'BOARD_LAYOUT'))
    throw new Error('Managed board view layout changed; reconcile manually');
  return { fields, definitions };
}

export async function configure(api, project, plan, profile = dedicated) {
  const { fields, definitions } = validateConfiguration(project, plan, profile);
  const colors = ['GRAY', 'BLUE', 'RED', 'YELLOW', 'GREEN'];
  for (const definition of definitions) {
    let field = fields.get(definition.key);
    const options = definition.options?.map((name, index) => ({
      name,
      description: name,
      color: colors[index],
    }));
    if (!field) {
      const input = { projectId: project.id, name: definition.name, dataType: definition.dataType };
      if (options) input.singleSelectOptions = options;
      if (definition.key === 'Sprint')
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
      fields.set(definition.key, field);
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
      fields.set(definition.key, field);
    }
    if (definition.key === 'Sprint') {
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
        fields.set(definition.key, result.projectV2Field);
      }
    }
  }
  const view = project.views.nodes.find((candidate) => candidate.name === profile.view);
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
          name: profile.view,
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
