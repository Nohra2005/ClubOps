import { beforeEach, describe, expect, it } from 'vitest';
import { ApiClient } from './client';
import { createMockTransport, type StorageLike } from './mock';

let storage: StorageLike;
beforeEach(() => {
  const values = new Map<string, string>();
  storage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => {
      values.set(key, value);
    },
  };
});
const client = (club = 'running-club', role = 'president' as const) =>
  new ApiClient(createMockTransport(storage, { club, role }, { delay: 0 }), 'demo');

describe('synthetic API safety boundaries', () => {
  it('accepts a starter text document as unverified and leaves its proposed contents in Review', async () => {
    const api = client('asme');
    const result = await api.upload(new File(['Synthetic club constitution'], 'constitution.md'));
    expect(result.tab).toBe('documents');
    expect(result.status).toBe('may_be_outdated');
    expect((await api.review()).some((card) => card.status === 'pending')).toBe(true);
  });
  it('resumes setup without spending and skips without proposing or charging', async () => {
    const api = client('asme');
    const before = await api.usage();
    expect((await api.setup()).index).toBe(1);
    expect((await api.setup()).index).toBe(1);
    expect((await api.setup('[skip]')).index).toBe(2);
    expect(await api.review()).toEqual([]);
    expect(await api.usage()).toEqual(before);
    await expect(api.setup(' ')).rejects.toMatchObject({ status: 422 });
    expect((await api.setup()).index).toBe(2);
    await api.setup('Synthetic society in the example faculty.');
    const restarted = client('asme');
    expect((await restarted.setup()).index).toBe(3);
    expect((await restarted.review())[0].status).toBe('pending');
    expect((await api.usage()).calls).toBe(before.calls + 1);
  });
  it('does not borrow another club’s chat answers or generated event tips', async () => {
    const asme = client('asme');
    expect((await asme.ask('What did we learn from the last run?')).kind).toBe('unknown');
    expect((await asme.ask('What does Cedar Coffee need?')).kind).toBe('unknown');
    const planned = await asme.plan('A synthetic ASME workshop');
    const run = await asme.run(planned.run_id);
    const event = await asme.event(run.event_id!);
    expect(JSON.stringify(event)).not.toContain('Cedar Coffee');
    expect(event.tips).toEqual([]);
    expect(event.task_count).toBe(event.tasks.length);
  });
  it('invalidates a guide sign-off when approved knowledge changes', async () => {
    const api = client();
    await api.signOff('president');
    expect((await api.handover('president')).signed_off_at).toBeTruthy();
    await api.decide('review-coffee', {
      decision: 'approve',
      opened_at: '2026-10-22T10:00:00Z',
      decided_at: '2026-10-22T10:01:00Z',
    });
    expect((await api.handover('president')).signed_off_at).toBeUndefined();
  });
  it('proposes shared-rule retirement without retiring the current rule', async () => {
    const api = client();
    await api.retire('kh-demo-venue');
    expect((await api.fact('kh-demo-venue')).status).toBe('current');
    expect(
      (await api.review()).some(
        (card) => card.title.startsWith('Retire:') && card.status === 'pending',
      ),
    ).toBe(true);
  });
  it('isolates persisted workspaces and refuses cross-club deep links', async () => {
    const running = client();
    const asme = client('asme');
    expect((await running.events()).length).toBeGreaterThan(0);
    expect(await asme.events()).toEqual([]);
    await expect(asme.event('ev-sunset-run')).rejects.toMatchObject({ status: 404 });
    await running.teach('A private synthetic running-club lesson.');
    expect(await asme.review()).toEqual([]);
  });
  it('does not spend or create calendar items when pages are read', async () => {
    const api = client();
    const before = await api.usage();
    await api.events();
    await api.knowledge('tips');
    await api.handover('president');
    await api.review();
    expect(await api.usage()).toEqual(before);
    expect((await api.calendar('2026-10')).items.some((i) => i.event_id === 'ev-sunset-run')).toBe(
      false,
    );
    await api.approvePlan('ev-sunset-run', 1);
    expect((await api.calendar('2026-10')).items.some((i) => i.event_id === 'ev-sunset-run')).toBe(
      true,
    );
  });
  it('refuses stale plan approval after editing details', async () => {
    const api = client();
    await api.editEvent('ev-sunset-run', { title: 'Changed event' });
    await expect(api.approvePlan('ev-sunset-run', 1)).rejects.toMatchObject({ status: 409 });
  });
  it('keeps AUB-wide rule proposals pending a second president', async () => {
    const api = client();
    const card = await api.decide('review-rule', {
      decision: 'approve',
      opened_at: '2026-10-22T10:00:00Z',
      decided_at: '2026-10-22T10:01:00Z',
    });
    expect(card.status).toBe('waiting_second_president');
    expect((await api.review()).find((r) => r.id === card.id)?.status).toBe(
      'waiting_second_president',
    );
  });
  it('rejects adviser mutations and strips cabinet contact details', async () => {
    const api = new ApiClient(
      createMockTransport(storage, { club: 'running-club', role: 'adviser' }, { delay: 0 }),
      'demo',
    );
    await expect(api.teach('An unapproved fact')).rejects.toMatchObject({ status: 403 });
    expect((await api.knowledge('contacts'))[0].contact?.email).toBeUndefined();
    expect((await api.fact('kh-demo-contact')).contact?.phone).toBeUndefined();
  });
});
