/** Synthetic turnover lifecycle. Never used as production authorization. */
import type { Member, Role } from '../api/types';
import { roles } from '../api/types';
import { ApiError } from '../api/errors';

export interface TurnoverInput {
  label: string;
  start_date: string;
  end_date: string;
  officers: { name: string; email: string; role: Role }[];
}
export interface TurnoverDraft extends TurnoverInput {
  id: string;
  phase: 'draft' | 'ready';
  reviewed_context?: string;
}
export interface CabinetTerm extends TurnoverInput {
  id: string;
  activated_at: string;
  previous_members: Member[];
  members: Member[];
  acknowledged: string[];
}
export interface TurnoverState {
  revision: number;
  draft: TurnoverDraft | null;
  active: CabinetTerm | null;
  history: CabinetTerm[];
}
export type TurnoverAction =
  | { kind: 'save'; revision: number; input: TurnoverInput }
  | { kind: 'review' | 'activate' | 'cancel'; revision: number; id: string }
  | { kind: 'acknowledge'; id: string };

export function localDate(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
export function initialTurnover(): TurnoverState {
  return { revision: 0, draft: null, active: null, history: [] };
}
function text(value: unknown, label: string, max: number) {
  if (typeof value !== 'string' || !value.trim() || value.trim().length > max)
    throw new ApiError(`Enter ${label}.`, 422);
  return value.trim();
}
function date(value: unknown) {
  if (
    typeof value !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}$/.test(value) ||
    !Number.isFinite(Date.parse(`${value}T12:00:00Z`)) ||
    new Date(`${value}T12:00:00Z`).toISOString().slice(0, 10) !== value
  )
    throw new ApiError('Enter valid term dates.', 422);
  return value;
}
export function validateTurnover(input: TurnoverInput): TurnoverInput {
  if (!input || typeof input !== 'object') throw new ApiError('Enter the next term.', 422);
  const label = text(input.label, 'a term name (up to 80 characters)', 80);
  const start_date = date(input.start_date);
  const end_date = date(input.end_date);
  if (end_date < start_date) throw new ApiError('The term must end on or after it starts.', 422);
  if (!Array.isArray(input.officers) || !input.officers.length || input.officers.length > 20)
    throw new ApiError('Add the incoming officers (up to 20).', 422);
  const officers = input.officers.map((officer) => {
    if (!officer || !roles.includes(officer.role) || officer.role === 'adviser')
      throw new ApiError('Choose a cabinet role for each incoming officer.', 422);
    const email = text(officer.email, 'each officer’s Google email', 254).toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      throw new ApiError('Enter a valid email for each incoming officer.', 422);
    return { name: text(officer.name, 'each officer’s name', 120), email, role: officer.role };
  });
  if (!officers.some((officer) => officer.role === 'president'))
    throw new ApiError('The incoming cabinet needs a president.', 422);
  if (new Set(officers.map((officer) => officer.email)).size !== officers.length)
    throw new ApiError('Use a different email for each incoming officer.', 422);
  return { label, start_date, end_date, officers };
}

export function applyTurnover(
  original: TurnoverState,
  members: Member[],
  actor: Member,
  action: TurnoverAction,
  today = localDate(),
  context = '',
) {
  const state = structuredClone(original);
  if (!action || !['save', 'review', 'activate', 'cancel', 'acknowledge'].includes(action.kind))
    throw new ApiError('Choose a valid turnover action.', 422);
  if (action.kind === 'acknowledge') {
    if (!state.active || state.active.id !== action.id)
      throw new ApiError('The active term changed. Refresh your workspace.', 409);
    if (!state.active.members.some((member) => member.member_id === actor.member_id))
      throw new ApiError('This introduction belongs to the incoming cabinet.', 403);
    if (!state.active.acknowledged.includes(actor.member_id)) {
      state.active.acknowledged.push(actor.member_id);
      state.revision++;
    }
    return { state, members };
  }
  if (actor.role !== 'president') throw new ApiError('Only a president manages turnover.', 403);
  if (!Number.isSafeInteger(action.revision) || action.revision !== state.revision)
    throw new ApiError('Turnover changed. Refresh before trying again.', 409);
  if (action.kind === 'save') {
    const input = validateTurnover(action.input);
    if (state.active && input.start_date <= state.active.end_date)
      throw new ApiError('The next term must start after the active term ends.', 422);
    state.draft = { ...input, id: state.draft?.id ?? crypto.randomUUID(), phase: 'draft' };
  } else {
    if (!state.draft || state.draft.id !== action.id)
      throw new ApiError('This turnover is no longer pending. Refresh the page.', 409);
    if (action.kind === 'cancel') state.draft = null;
    else if (action.kind === 'review') {
      state.draft.phase = 'ready';
      state.draft.reviewed_context = context;
    } else {
      if (state.draft.phase !== 'ready')
        throw new ApiError('Review this draft before activating.', 409);
      if (state.draft.reviewed_context !== context)
        throw new ApiError('Work or cabinet changed. Edit and review the draft again.', 409);
      if (today < state.draft.start_date || today > state.draft.end_date)
        throw new ApiError(
          'Activate during the next term’s dates. Nothing changes automatically.',
          422,
        );
      const draft = state.draft;
      const incoming = draft.officers.map((officer) => ({
        ...officer,
        member_id:
          members.find((member) => member.email.toLowerCase() === officer.email)?.member_id ??
          crypto.randomUUID(),
      }));
      const advisers = members.filter((member) => member.role === 'adviser');
      if (
        advisers.some((adviser) =>
          incoming.some((member) => member.email === adviser.email.toLowerCase()),
        )
      )
        throw new ApiError(
          'Change the adviser’s assignment in Cabinet before including them here.',
          422,
        );
      if (state.active) state.history.push(state.active);
      state.active = {
        label: draft.label,
        start_date: draft.start_date,
        end_date: draft.end_date,
        officers: draft.officers,
        id: draft.id,
        activated_at: new Date().toISOString(),
        previous_members: structuredClone(members),
        members: incoming,
        acknowledged: [],
      };
      state.draft = null;
      state.revision++;
      return { state, members: [...incoming, ...advisers] };
    }
  }
  state.revision++;
  return { state, members };
}
