import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../api/client';
import { createMockTransport, workspaceKey, type StorageLike } from '../api/mock';
import type { Member, Workspace } from '../api/types';
import {
  applyTurnover,
  initialTurnover,
  validateTurnover,
  type TurnoverInput,
  type TurnoverState,
} from './model';

const president: Member = {
  member_id: 'old-p',
  name: 'Outgoing Example',
  email: 'outgoing@example.com',
  role: 'president',
};
const treasurer: Member = {
  member_id: 'old-t',
  name: 'Treasurer Example',
  email: 'treasurer@example.com',
  role: 'treasurer',
};
const roster = [president, treasurer];
const input = (): TurnoverInput => ({
  label: 'Example term',
  start_date: '2027-01-01',
  end_date: '2027-06-30',
  officers: [{ name: 'Incoming Example', email: 'incoming@example.com', role: 'president' }],
});
function prepared() {
  const saved = applyTurnover(initialTurnover(), roster, president, {
    kind: 'save',
    revision: 0,
    input: input(),
  });
  return applyTurnover(
    saved.state,
    roster,
    president,
    { kind: 'review', revision: 1, id: saved.state.draft!.id },
    '2027-01-01',
    'work-v1',
  ).state;
}
const activate = (
  state: TurnoverState,
  members = roster,
  actor = president,
  today = '2027-01-01',
  context = 'work-v1',
) =>
  applyTurnover(
    state,
    members,
    actor,
    { kind: 'activate', revision: state.revision, id: state.draft!.id },
    today,
    context,
  );

describe('C-39 synthetic term lifecycle', () => {
  it('preserves the cabinet until explicit activation and never mutates its input', () => {
    const ready = prepared();
    expect(ready.active).toBeNull();
    expect(roster[0]).toEqual(president);
    const next = activate(ready);
    expect(next.state.draft).toBeNull();
    expect(next.state.active?.previous_members).toEqual(roster);
    expect(next.members[0].name).toBe('Incoming Example');
    expect(next.members.some((member) => member.email === president.email)).toBe(false);
    expect(ready.active).toBeNull();
  });
  it('rejects stale, unreviewed, changed-work and duplicate activation without changing the prior state', () => {
    const ready = prepared();
    expect(() =>
      applyTurnover(ready, roster, president, {
        kind: 'activate',
        revision: 1,
        id: ready.draft!.id,
      }),
    ).toThrow('changed');
    expect(() => activate(ready, roster, president, '2027-01-01', 'work-v2')).toThrow(
      'Work or cabinet changed',
    );
    const edited = applyTurnover(ready, roster, president, {
      kind: 'save',
      revision: ready.revision,
      input: { ...input(), label: 'Edited' },
    }).state;
    expect(edited.draft?.phase).toBe('draft');
    expect(() => activate(edited)).toThrow('Review');
    const next = activate(ready);
    expect(() =>
      applyTurnover(next.state, next.members, next.members[0], {
        kind: 'activate',
        revision: ready.revision,
        id: ready.draft!.id,
      }),
    ).toThrow('changed');
    expect(next.state.history).toHaveLength(0);
  });
  it('requires a president for every administrative transition', () => {
    const ready = prepared();
    for (const action of [
      { kind: 'save' as const, revision: 2, input: input() },
      ...(['review', 'cancel', 'activate'] as const).map((kind) => ({
        kind,
        revision: 2,
        id: ready.draft!.id,
      })),
    ])
      expect(() => applyTurnover(ready, roster, treasurer, action)).toThrow('Only a president');
  });
  it('dates never activate a term and activation outside its dates is rejected', () => {
    const ready = prepared();
    expect(() => activate(ready, roster, president, '2026-12-31')).toThrow('Activate during');
    expect(() => activate(ready, roster, president, '2027-07-01')).toThrow('Activate during');
    expect(ready.active).toBeNull();
  });
  it('cancels a pending draft without replacing the cabinet', () => {
    const ready = prepared();
    const next = applyTurnover(ready, roster, president, {
      kind: 'cancel',
      id: ready.draft!.id,
      revision: ready.revision,
    });
    expect(next.state.draft).toBeNull();
    expect(next.state.active).toBeNull();
    expect(next.members).toEqual(roster);
  });
  it('keeps a real history across terms and rejects overlapping dates', () => {
    const first = activate(prepared());
    expect(() =>
      applyTurnover(first.state, first.members, first.members[0], {
        kind: 'save',
        revision: first.state.revision,
        input: input(),
      }),
    ).toThrow('after the active term');
    const secondInput = {
      ...input(),
      label: 'Next example term',
      start_date: '2027-07-01',
      end_date: '2027-12-31',
    };
    let second = applyTurnover(first.state, first.members, first.members[0], {
      kind: 'save',
      revision: first.state.revision,
      input: secondInput,
    }).state;
    second = applyTurnover(
      second,
      first.members,
      first.members[0],
      { kind: 'review', revision: second.revision, id: second.draft!.id },
      '2027-07-01',
      'work-v1',
    ).state;
    const next = activate(second, first.members, first.members[0], '2027-07-01');
    expect(next.state.history).toEqual([first.state.active]);
    expect(next.state.active?.id).not.toBe(first.state.active?.id);
    expect(next.state.active?.acknowledged).toEqual([]);
  });
  it('acknowledges only the incoming member and active term, idempotently', () => {
    const next = activate(prepared());
    const ack = { kind: 'acknowledge' as const, id: next.state.active!.id };
    expect(() => applyTurnover(next.state, next.members, president, ack)).toThrow(
      'incoming cabinet',
    );
    expect(() =>
      applyTurnover(next.state, next.members, next.members[0], { ...ack, id: 'former-term' }),
    ).toThrow('active term changed');
    const acknowledged = applyTurnover(next.state, next.members, next.members[0], ack);
    expect(acknowledged.state.active?.acknowledged).toEqual([next.members[0].member_id]);
    expect(applyTurnover(acknowledged.state, next.members, next.members[0], ack).state).toEqual(
      acknowledged.state,
    );
  });
  it('rejects missing president, duplicate identity, invalid dates and unsupported roles', () => {
    const valid = input();
    for (const invalid of [
      { ...valid, officers: [] },
      { ...valid, officers: [{ ...valid.officers[0], role: 'treasurer' as const }] },
      {
        ...valid,
        officers: [valid.officers[0], { ...valid.officers[0], email: 'INCOMING@example.com' }],
      },
      { ...valid, start_date: '2027-02-30' },
      { ...valid, end_date: '2026-01-01' },
      { ...valid, officers: [{ ...valid.officers[0], role: 'adviser' as const }] },
    ])
      expect(() => validateTurnover(invalid)).toThrow();
    expect(() =>
      applyTurnover(initialTurnover(), roster, president, { kind: 'unexpected' } as never),
    ).toThrow('valid turnover action');
  });
});

describe('demo transport and production boundary', () => {
  function store() {
    const values = new Map<string, string>();
    return {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => {
        values.set(key, value);
      },
    } satisfies StorageLike;
  }
  it('F-506: HTTP never sends an invented turnover route or trusts local term metadata', async () => {
    const transport = vi.fn();
    const api = new ApiClient(transport, 'http');
    await expect(api.turnover()).rejects.toMatchObject({ status: 501 });
    await expect(
      api.changeTurnover({ kind: 'save', revision: 0, input: input() }),
    ).rejects.toMatchObject({ status: 501 });
    expect(transport).not.toHaveBeenCalled();
  });
  it('F-507: activation persists as one workspace save, preserving work, knowledge and charges', async () => {
    const storage = store();
    const make = (club = 'running-club') =>
      new ApiClient(
        createMockTransport(storage, { club, role: 'president' }, { delay: 0 }),
        'demo',
      );
    const api = make();
    await api.me();
    const before = JSON.parse(storage.getItem(workspaceKey('running-club'))!) as Workspace;
    const today = new Date();
    const label = (await import('./model')).localDate(today);
    const candidate = {
      ...input(),
      start_date: label,
      end_date: `${today.getFullYear() + 1}-12-31`,
    };
    let state = await api.changeTurnover({ kind: 'save', revision: 0, input: candidate });
    state = await api.changeTurnover({
      kind: 'review',
      revision: state.revision,
      id: state.draft!.id,
    });
    await api.changeTurnover({ kind: 'activate', revision: state.revision, id: state.draft!.id });
    const after = JSON.parse(storage.getItem(workspaceKey('running-club'))!) as Workspace;
    for (const key of ['events', 'knowledge', 'review', 'runs', 'usage', 'connected'] as const)
      expect(after[key]).toEqual(before[key]);
    expect((await make().me()).user.name).toBe('Incoming Example');
    expect((await make().me()).demo_term?.acknowledged).toBe(false);
    expect((await make('asme').turnover()).active).toBeNull();
    await api.changeTurnover({ kind: 'acknowledge', id: after.turnover!.active!.id });
    expect((await make().me()).demo_term?.acknowledged).toBe(true);
  });
});
