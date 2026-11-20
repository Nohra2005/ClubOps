import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from '../api/client';
import { readSkippedEmail, readWaitingEmail } from './http-metadata';

describe('read-only Inbox metadata', () => {
  it('projects documented fields only and treats missing descriptive labels as unavailable', () => {
    const row = {
      id: 'synthetic-1',
      subject: '<img src=x onerror=unsafe()>',
      body: 'private canary',
    };
    expect(readWaitingEmail([row])).toEqual([
      { id: row.id, subject: row.subject, date: null, forwarded_by: null },
    ]);
    expect(
      readSkippedEmail([{ ...row, reason: 'new_reason', why: 'A plain server explanation' }]),
    ).toEqual([
      { id: row.id, subject: row.subject, reason: 'new_reason', why: 'A plain server explanation' },
    ]);
  });

  it.each([
    null,
    {},
    { items: [] },
    [null],
    [{ id: '', subject: 'Synthetic' }],
    [
      { id: 'same', subject: 'One' },
      { id: 'same', subject: 'Two' },
    ],
    [{ id: 'bad', subject: 'Synthetic', date: { private: 'canary' } }],
  ])('rejects incompatible or ambiguous lists without echoing their contents (%j)', (value) => {
    expect(() => readWaitingEmail(value)).toThrow('Inbox metadata could not be understood.');
  });

  it('rejects malformed skip reasons instead of presenting an empty successful list', () => {
    expect(() =>
      readSkippedEmail([{ id: 'one', subject: 'Synthetic', reason: [], why: 'canary' }]),
    ).toThrow('Inbox metadata could not be understood.');
  });

  it('uses only the documented metadata GET routes and never falls back to a demo or paid read', async () => {
    const transport = vi.fn().mockResolvedValue([]);
    const api = new ApiClient(transport, 'http');
    await expect(api.inbox()).resolves.toEqual([]);
    await expect(api.skippedInbox()).resolves.toEqual([]);
    expect(transport.mock.calls).toEqual([
      ['/inbox', undefined],
      ['/inbox/skipped', undefined],
    ]);
    const demo = new ApiClient(transport, 'demo');
    await expect(demo.inbox()).rejects.toMatchObject({ status: 501 });
    await expect(demo.skippedInbox()).rejects.toMatchObject({ status: 501 });
    expect(transport).toHaveBeenCalledTimes(2);
  });
});
