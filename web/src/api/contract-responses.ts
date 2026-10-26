/** Published capability contracts -> screen models. HTTP endpoint envelopes remain part of T-22. */
import { ApiError } from './errors';
import type { AgentRun, AgentStep, ChatReply, Draft, DraftType, Source } from './types';

const incompatible = () =>
  new ApiError(
    'ClubOps returned incompatible data. Your edits are still here. Please try again.',
    502,
  );

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw incompatible();
  return value as Record<string, unknown>;
}

function text(value: unknown, max: number, min = 0): string {
  if (typeof value !== 'string' || value.trim().length < min || value.length > max)
    throw incompatible();
  return value;
}

function decimal(value: unknown): number {
  if (
    typeof value !== 'number' &&
    !(typeof value === 'string' && /^(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(value))
  )
    throw incompatible();
  const result = Number(value);
  if (!Number.isFinite(result) || result < 0) throw incompatible();
  return result;
}

function itemIds(value: unknown): string[] {
  if (value === undefined) return [];
  if (
    !Array.isArray(value) ||
    value.some((id) => typeof id !== 'string' || !/^kh-[a-z0-9-]{2,63}$/.test(id))
  )
    throw incompatible();
  return value as string[];
}

function payload(
  value: unknown,
  allowQuestion = false,
): { data: Record<string, unknown>; fallback: boolean; needsInput?: boolean } {
  const envelope = object(value);
  // AgentRun itself can have status=failed; only Result has data/error alongside that status.
  if (allowQuestion && Object.hasOwn(envelope, 'run_id'))
    return { data: envelope, fallback: false };
  if (!['ok', 'needs_input', 'failed'].includes(String(envelope.status)))
    return { data: envelope, fallback: false };
  if (envelope.status === 'failed') {
    const code = object(envelope.error).code;
    const status =
      code === 'not_authorized'
        ? 403
        : ['stale_input', 'conflict'].includes(String(code))
          ? 409
          : 502;
    throw new ApiError(
      status === 403
        ? "You don't have permission for this action."
        : status === 409
          ? 'This item changed. Reload it before approving.'
          : "ClubOps couldn't finish this. Your edits are still on this page.",
      status,
    );
  }
  if (envelope.status === 'needs_input' && (!allowQuestion || !envelope.data))
    throw new ApiError(
      'ClubOps needs more information before it can finish. Your edits are still here.',
      422,
    );
  return {
    data: object(envelope.data),
    fallback: envelope.degraded === true,
    needsInput: envelope.status === 'needs_input',
  };
}

export const runStatuses = {
  running: 'working',
  waiting_for_user: 'waiting_for_user',
  done: 'done',
  at_limit: 'limit_reached',
  failed: 'failed',
} as const satisfies Record<string, AgentRun['status']>;
export const stepStates = ['running', 'done', 'question', 'failed'] as const;

export function readAgentRun(value: unknown, expectedId: string): AgentRun {
  const { data, fallback, needsInput } = payload(value, true);
  const runId = text(data.run_id, 64, 2);
  text(data.club_id, 64, 2);
  if (
    runId !== expectedId ||
    typeof data.status !== 'string' ||
    !Object.hasOwn(runStatuses, data.status)
  )
    throw incompatible();
  if (!Array.isArray(data.steps)) throw incompatible();
  const steps: AgentStep[] = data.steps.map((entry, index) => {
    const step = object(entry);
    if (step.n !== index + 1 || !stepStates.includes(step.state as (typeof stepStates)[number]))
      throw incompatible();
    return {
      n: index + 1,
      tool: text(step.tool, 64, 2),
      text: text(step.text, 200),
      state: step.state as (typeof stepStates)[number],
    };
  });
  const stepLimit = decimal(data.step_limit);
  const stepsUsed = decimal(data.steps_used);
  const costLimit = decimal(data.cost_limit_usd);
  if (
    !Number.isInteger(stepLimit) ||
    stepLimit < 1 ||
    !Number.isInteger(stepsUsed) ||
    stepsUsed > stepLimit ||
    costLimit <= 0
  )
    throw incompatible();
  const status = runStatuses[data.status as keyof typeof runStatuses];
  if (needsInput && !['waiting_for_user', 'limit_reached'].includes(status)) throw incompatible();
  const question = steps.at(-1)?.state === 'question' ? steps.at(-1)!.text : undefined;
  if ((status === 'waiting_for_user') !== (question !== undefined)) throw incompatible();
  const eventId = data.event_id == null ? undefined : text(data.event_id, 66, 5);
  if (status === 'done' && !eventId) throw incompatible();
  return {
    run_id: runId,
    status,
    steps,
    steps_used: stepsUsed,
    step_limit: stepLimit,
    cost_usd: decimal(data.cost_usd),
    cost_limit_usd: costLimit,
    event_id: eventId,
    ...(question !== undefined ? { question: { text: question, kind: 'text' } } : {}),
    fallback,
  };
}

export function readAnswer(value: unknown): ChatReply {
  const { data, fallback: degraded } = payload(value);
  const fallback = degraded || data.fallback === true;
  const answer = text(data.text, 1500);
  if (data.kind === 'learned')
    return { kind: 'learned', text: answer, review_id: text(data.review_id, 200, 1) };
  if (data.kind !== undefined && data.kind !== (data.known ? 'answer' : 'unknown'))
    throw incompatible();
  const citations: Source[] =
    data.kind === 'answer' && Array.isArray(data.citations)
      ? data.citations.map((value) => {
          const source = object(value);
          const item_id = itemIds([source.item_id])[0];
          return {
            item_id,
            label: text(source.label, 300, 1),
            ...(source.quote == null ? {} : { quote: text(source.quote, 5000) }),
            kind: ['document', 'email', 'note', 'debrief'].includes(String(source.kind))
              ? (source.kind as Source['kind'])
              : undefined,
            authority: ['official_document', 'office_email', 'stated_by_president'].includes(
              String(source.authority),
            )
              ? (source.authority as Source['authority'])
              : undefined,
          };
        })
      : itemIds(data.citations).map((item_id) => ({ item_id, label: item_id }));
  if (data.known === true) {
    if (
      !citations.length ||
      !['verified', 'single_source', 'disputed'].includes(String(data.basis))
    )
      throw incompatible();
    return {
      kind: 'answer',
      known: true,
      text: answer,
      basis: data.basis as 'verified' | 'single_source' | 'disputed',
      citations,
      ...(data.review_id == null ? {} : { review_id: text(data.review_id, 200, 1) }),
      fallback,
    };
  }
  if (data.known !== false || data.basis !== 'none' || citations.length) throw incompatible();
  const ask = object(data.ask);
  return {
    kind: 'unknown',
    known: false,
    text: answer,
    basis: 'none',
    ask: { who: text(ask.who, 120, 2), role: ask.role == null ? null : text(ask.role, 120) },
    look_in: data.look_in == null ? null : text(data.look_in, 200),
    fallback,
  };
}

export const draftTypes = {
  whatsapp_announcement: 'announcement',
  reminder_message: 'reminder',
  sponsor_email: 'sponsor_email',
  instagram_caption: 'instagram',
  poster_text: 'poster',
  expense_form: 'expense',
  volunteer_shifts: 'volunteers',
  impact_report: 'impact_report',
} as const satisfies Record<string, DraftType>;

export function readDraft(value: unknown, eventId: string, type: DraftType): Draft {
  const { data } = payload(value);
  if (
    data.event_id !== eventId ||
    typeof data.draft_type !== 'string' ||
    !Object.hasOwn(draftTypes, data.draft_type)
  )
    throw incompatible();
  if (
    draftTypes[data.draft_type as keyof typeof draftTypes] !== type ||
    (data.state !== undefined && data.state !== 'draft')
  )
    throw incompatible();
  const subject = data.subject == null ? undefined : text(data.subject, 200);
  if ((type === 'sponsor_email') !== (subject !== undefined)) throw incompatible();
  return {
    type,
    text: text(data.body, 5000, 1),
    subject,
    template_version: text(data.template_version, 40),
    based_on: itemIds(data.based_on),
    state: 'draft',
  };
}
