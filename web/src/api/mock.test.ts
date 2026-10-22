import { beforeEach, describe, expect, it } from 'vitest';
import { ApiClient } from './client';
import { createMockTransport, type StorageLike } from './mock';

let storage: StorageLike;
beforeEach(() => { const values = new Map<string,string>(); storage = { getItem: key => values.get(key) ?? null, setItem: (key,value) => { values.set(key,value); } }; });
const client = (club = 'running-club', role = 'president' as const) => new ApiClient(createMockTransport(storage, { club, role }, { delay: 0 }), 'demo');

describe('synthetic API safety boundaries', () => {
  it('isolates persisted workspaces and refuses cross-club deep links', async () => {
    const running = client(); const asme = client('asme');
    expect((await running.events()).length).toBeGreaterThan(0);
    expect(await asme.events()).toEqual([]);
    await expect(asme.event('ev-sunset-run')).rejects.toMatchObject({ status: 404 });
    await running.teach('A private synthetic running-club lesson.');
    expect(await asme.review()).toEqual([]);
  });
  it('does not spend or create calendar items when pages are read', async () => {
    const api = client(); const before = await api.usage();
    await api.events(); await api.knowledge('tips'); await api.handover('president'); await api.review();
    expect(await api.usage()).toEqual(before);
    expect((await api.calendar('2026-10')).items.some(i => i.event_id === 'ev-sunset-run')).toBe(false);
    await api.approvePlan('ev-sunset-run', 1);
    expect((await api.calendar('2026-10')).items.some(i => i.event_id === 'ev-sunset-run')).toBe(true);
  });
  it('refuses stale plan approval after editing details', async () => {
    const api = client(); await api.editEvent('ev-sunset-run', { title: 'Changed event' });
    await expect(api.approvePlan('ev-sunset-run', 1)).rejects.toMatchObject({ status: 409 });
  });
  it('keeps AUB-wide rule proposals pending a second president', async () => {
    const api = client(); const card = await api.decide('review-rule', { decision: 'approve', opened_at: '2026-10-22T10:00:00Z', decided_at: '2026-10-22T10:01:00Z' });
    expect(card.status).toBe('waiting_second_president');
    expect((await api.review()).find(r => r.id === card.id)?.status).toBe('waiting_second_president');
  });
  it('rejects adviser mutations and strips cabinet contact details', async () => {
    const api = new ApiClient(createMockTransport(storage, { club: 'running-club', role: 'adviser' }, { delay: 0 }), 'demo');
    await expect(api.teach('An unapproved fact')).rejects.toMatchObject({ status: 403 });
    expect((await api.knowledge('contacts'))[0].contact?.email).toBeUndefined();
    expect((await api.fact('kh-demo-contact')).contact?.phone).toBeUndefined();
  });
});
