import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiClient, httpTransport } from './client';
import { readInboxCapture, readRestoreAcknowledgement, validRestoreDate } from './action-responses';

afterEach(() => vi.unstubAllGlobals());

describe('documented Inbox capture results', () => {
  it.each([
    { proposals: ['p-1', 'p-2'], skipped: [] },
    { proposals: [], skipped: [] },
    { proposals: [], skipped: ['Synthetic unusable material'] },
    { proposals: ['p-1', 'p-1'], skipped: ['Synthetic unused fragment'] },
  ])('preserves successful/no-fact/skipped/mixed acknowledgements (%j)', (value) => {
    expect(readInboxCapture({ ...value, body: 'PRIVATE_CANARY' })).toEqual(value);
  });

  it.each([
    null,
    {},
    { proposals: [], skipped: 'wrong' },
    { proposals: [1], skipped: [] },
    { proposals: [''], skipped: [] },
    { proposals: [], skipped: [null] },
  ])('rejects an unconfirmed result without an automatic second request (%j)', async (value) => {
    const transport = vi.fn().mockResolvedValue(value);
    await expect(new ApiClient(transport, 'http').captureInbox('msg/a')).rejects.toMatchObject({
      status: 502,
    });
    expect(transport.mock.calls).toEqual([
      ['/inbox/msg%2Fa/capture', { method: 'POST', body: undefined }],
    ]);
  });
});

describe('Restore acknowledgement and date boundary', () => {
  it('accepts only this club fact becoming current and drops the unconsumed projection', () => {
    expect(
      readRestoreAcknowledgement(
        { item_id: 'k-1', scope: 'club', status: 'current', title: 'Synthetic', private: 'canary' },
        'k-1',
      ),
    ).toEqual({ item_id: 'k-1', scope: 'club', status: 'current' });
  });
  it.each([
    { item_id: 'other', scope: 'club', status: 'current' },
    { item_id: 'k-1', scope: 'aub', status: 'current' },
    { item_id: 'k-1', scope: 'club', status: 'may_be_outdated' },
    null,
  ])('rejects wrong identity/scope/state acknowledgements (%j)', (value) => {
    expect(() => readRestoreAcknowledgement(value, 'k-1')).toThrow('Restore was not confirmed.');
  });
  it.each(['2026-02-31', '0000-01-01', 'not-a-date', '2027-06-30T00:00:00Z', undefined])(
    'rejects malformed date-only values before transport (%s)',
    (value) => expect(validRestoreDate(value)).toBe(false),
  );
  it('accepts a genuine date and explicit no-end-date', () => {
    expect(validRestoreDate('2028-02-29')).toBe(true);
    expect(validRestoreDate(null)).toBe(true);
  });
});

describe('protected write transport', () => {
  it('uses only the documented encoded routes, cookies and CSRF header', async () => {
    const fetcher = vi
      .fn()
      .mockImplementation(async (url: string) =>
        Response.json(
          url.includes('/inbox/')
            ? { proposals: [], skipped: [] }
            : { item_id: 'k/a', scope: 'club', status: 'current' },
        ),
      );
    vi.stubGlobal('fetch', fetcher);
    const api = new ApiClient(httpTransport(), 'http');
    await api.captureInbox('msg/a');
    await api.restoreFact('k/a', null);
    expect(fetcher.mock.calls[0][0]).toBe('/api/inbox/msg%2Fa/capture');
    expect(fetcher.mock.calls[1][0]).toBe('/api/knowledge/k%2Fa/restore');
    expect(fetcher.mock.calls[0][1].body).toBeUndefined();
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ valid_to: null });
    for (const [, options] of fetcher.mock.calls) {
      expect(options.method).toBe('POST');
      expect(options.credentials).toBe('include');
      expect(options.headers['X-Requested-With']).toBe('ClubOps');
    }
  });
  it('preserves public Restore 4xx explanations while other actions keep generic errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation(async () =>
          Response.json({ detail: 'Synthetic disputed fact: review it first.' }, { status: 409 }),
        ),
    );
    const api = new ApiClient(httpTransport(), 'http');
    await expect(api.restoreFact('k-1', null)).rejects.toThrow(
      'Synthetic disputed fact: review it first.',
    );
    await expect(api.logout()).rejects.not.toThrow('Synthetic disputed fact');
  });
  it('never exposes server diagnostics for 5xx even on Restore', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(Response.json({ detail: 'PRIVATE_SERVER_CANARY' }, { status: 500 })),
    );
    await expect(
      new ApiClient(httpTransport(), 'http').restoreFact('k-1', null),
    ).rejects.not.toThrow('PRIVATE_SERVER_CANARY');
  });
});
