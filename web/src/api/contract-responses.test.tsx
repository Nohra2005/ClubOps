import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import planSchema from '../../../schemas/plan-event.response.json';
import draftSchema from '../../../schemas/draft.response.json';
import {
  readAgentRun,
  readAnswer,
  readDraft,
  readSetupStep,
  runStatuses,
  stepStates,
  draftTypes,
} from './contract-responses';
import { AgentSteps } from '../components/AgentSteps';
import { NotSure } from '../components/ui';
import type { DraftType } from './types';

const run = {
  run_id: 'run-contract-check',
  club_id: 'running-club',
  event_id: 'ev-contract-check',
  status: 'running',
  steps: [{ n: 1, tool: 'search-memory', text: 'Read the approved notes', state: 'running' }],
  steps_used: 1,
  step_limit: 8,
  cost_usd: '0.006',
  cost_limit_usd: '0.025',
};
const unknownAnswer = {
  known: false,
  text: 'Ask the office about this specific case.',
  basis: 'none',
  citations: [],
  ask: { who: 'Example office', role: null },
  look_in: null,
};
const draft = {
  event_id: 'ev-contract-check',
  draft_type: 'sponsor_email',
  template_version: 'synthetic-1',
  subject: 'Synthetic event request',
  body: 'A synthetic draft for a person to review.',
  based_on: ['kh-contract-example'],
  state: 'draft',
};

describe('published 0.2.0 contract responses', () => {
  it('rejects malformed setup progress instead of clearing the answer or showing completion', () => {
    const step = {
      question: 'Synthetic question',
      index: 2,
      total: 10,
      done: false,
      rules_count: 25,
    };
    expect(readSetupStep(step)).toEqual(step);
    for (const change of [
      { index: 0 },
      { index: 11 },
      { total: 0 },
      { index: 1.5 },
      { done: true },
      { done: 'false' },
      { rules_count: -1 },
      { question: '' },
    ])
      expect(() => readSetupStep({ ...step, ...change })).toThrow('incompatible data');
    expect(readSetupStep({ ...step, index: 10, done: true }).done).toBe(true);
  });
  it('preserves the published HTTP chat view model with expanded citations and review links', () => {
    const reply = readAnswer({
      kind: 'answer',
      known: true,
      text: 'A disputed synthetic answer.',
      basis: 'disputed',
      review_id: 'review-example',
      fallback: true,
      citations: [
        {
          item_id: 'kh-example-note',
          label: 'Synthetic cabinet note',
          quote: 'A fictional excerpt.',
          kind: 'note',
        },
      ],
    });
    expect(reply).toMatchObject({
      kind: 'answer',
      review_id: 'review-example',
      fallback: true,
      citations: [
        {
          item_id: 'kh-example-note',
          label: 'Synthetic cabinet note',
          quote: 'A fictional excerpt.',
          kind: 'note',
        },
      ],
    });
    expect(
      readAnswer({ kind: 'learned', text: 'Proposed for review.', review_id: 'review-example' }),
    ).toEqual({ kind: 'learned', text: 'Proposed for review.', review_id: 'review-example' });
    expect(() =>
      readAnswer({
        kind: 'answer',
        known: true,
        text: 'Unusable source',
        basis: 'verified',
        citations: [{ label: 'No item ID' }],
      }),
    ).toThrow('incompatible data');
  });
  it('tracks every published run, step and draft enum instead of drifting silently', () => {
    expect(Object.keys(runStatuses)).toEqual(planSchema.$defs.RunStatus.enum);
    expect([...stepStates]).toEqual(planSchema.$defs.StepState.enum);
    expect(Object.keys(draftTypes)).toEqual(draftSchema.$defs.DraftType.enum);
  });

  it.each(Object.entries(runStatuses))(
    'renders the published run state %s as %s',
    (wire, screen) => {
      const stepState =
        wire === 'waiting_for_user' ? 'question' : wire === 'failed' ? 'failed' : 'done';
      const result = readAgentRun(
        { ...run, status: wire, steps: [{ ...run.steps[0], state: stepState }] },
        run.run_id,
      );
      expect(result.status).toBe(screen);
      expect(result.cost_usd).toBe(0.006);
      expect(result.cost_limit_usd).toBe(0.025);
      const markup = renderToStaticMarkup(<AgentSteps run={result} onAnswer={() => {}} />);
      expect(markup).toContain('$0.025');
      if (wire === 'waiting_for_user') expect(markup).toContain('Your answer');
      if (wire === 'failed') expect(markup).toContain('This run failed.');
    },
  );

  it('preserves the fallback and final question in a needs-input result', () => {
    const result = readAgentRun(
      {
        status: 'needs_input',
        degraded: true,
        data: {
          ...run,
          status: 'waiting_for_user',
          steps: [{ ...run.steps[0], state: 'question', text: 'Will there be prizes?' }],
        },
      },
      run.run_id,
    );
    expect(result.question).toEqual({ kind: 'text', text: 'Will there be prizes?' });
    expect(result.fallback).toBe(true);
  });

  it('refuses inconsistent runs, other run IDs, non-finite money and unknown states', () => {
    for (const change of [
      { run_id: 'run-other' },
      { status: 'waiting_for_user' },
      { status: 'unknown-state' },
      { status: 'done', event_id: null },
      { cost_usd: 'NaN' },
      { cost_limit_usd: 0 },
      { steps_used: 9 },
      { steps: [{ ...run.steps[0], n: 2 }] },
    ])
      expect(() => readAgentRun({ ...run, ...change }, run.run_id)).toThrow('incompatible data');
  });

  it('shows a valid unknown answer without inventing a role or place to look', () => {
    const result = readAnswer(unknownAnswer);
    expect(result).toMatchObject({
      kind: 'unknown',
      ask: { who: 'Example office', role: null },
      look_in: null,
    });
    if (result.kind !== 'unknown') throw new Error('Expected an unknown answer');
    const markup = renderToStaticMarkup(<NotSure ask={result.ask} lookIn={result.look_in} />);
    expect(markup).toContain('Example office');
    expect(markup).not.toContain('Look in');
    expect(markup).not.toContain('null');
    expect(() => readAnswer({ ...unknownAnswer, ask: null })).toThrow('incompatible data');
  });

  it('keeps real citation identifiers and the degraded marker without inventing source quotes', () => {
    const result = readAnswer({
      status: 'ok',
      degraded: true,
      data: {
        known: true,
        text: 'A sourced synthetic answer.',
        basis: 'verified',
        citations: ['kh-contract-example'],
      },
    });
    expect(result).toMatchObject({
      kind: 'answer',
      fallback: true,
      citations: [{ item_id: 'kh-contract-example', label: 'kh-contract-example' }],
    });
    expect(() => readAnswer({ known: true, text: 'Uncited', basis: 'verified' })).toThrow(
      'incompatible data',
    );
  });

  it.each(Object.entries(draftTypes))(
    'maps draft type %s to %s and preserves its provenance',
    (wire, screen) => {
      const result = readDraft(
        { ...draft, draft_type: wire, subject: wire === 'sponsor_email' ? draft.subject : null },
        draft.event_id,
        screen as DraftType,
      );
      expect(result).toMatchObject({
        type: screen,
        text: draft.body,
        based_on: draft.based_on,
        template_version: draft.template_version,
        state: 'draft',
      });
      expect(result.updated_at).toBeUndefined();
      expect(result.recipient).toBeUndefined();
    },
  );

  it('refuses sent, wrong-event and wrong-type drafts, preserving the current draft on failure', () => {
    for (const change of [
      { state: 'sent' },
      { event_id: 'ev-other' },
      { draft_type: 'poster_text' },
      { body: '' },
    ])
      expect(() => readDraft({ ...draft, ...change }, draft.event_id, 'sponsor_email')).toThrow(
        'incompatible data',
      );
  });

  it('accepts the published no-fact teaching reply without inventing a review target', () => {
    expect(
      readAnswer({ kind: 'learned', text: 'No supported new fact was found.', review_id: '' }),
    ).toEqual({ kind: 'learned', text: 'No supported new fact was found.', review_id: '' });
    expect(() => readAnswer({ kind: 'learned', text: 'Malformed reply', review_id: null })).toThrow(
      'incompatible data',
    );
  });

  it('does not treat HTTP-200 failure envelopes or blocking questions as successful answers', () => {
    expect(() =>
      readAnswer({
        status: 'failed',
        error: { code: 'not_authorized', message: 'Private diagnostic details' },
        data: null,
      }),
    ).toThrow("don't have permission");
    expect(() =>
      readDraft({ status: 'needs_input', data: draft }, draft.event_id, 'sponsor_email'),
    ).toThrow('needs more information');
    expect(() => readAnswer({ status: 'ok', data: null })).toThrow('incompatible data');
  });
});
