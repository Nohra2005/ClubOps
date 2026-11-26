import { afterEach, vi } from 'vitest';
import { ApiClient, httpTransport } from './client';
afterEach(() => vi.unstubAllGlobals());
import { describe, expect, it } from 'vitest';
import {
  readGoogleConnection,
  readGoogleAuthorization,
  readInboxFetch,
} from './google-connections';

describe('Google connection response boundaries', () => {
  it('accepts the four server states and only documented metadata', () => {
    for (const state of ['not_set_up', 'not_connected', 'connected', 'reconnect']) {
      expect(
        readGoogleConnection(
          { state, source: null, can_connect: false, can_manage: true, key: 'PRIVATE' },
          'gmail',
        ),
      ).toEqual({ state, source: null, can_connect: false, can_manage: true });
    }
    expect(
      readGoogleConnection(
        { state: 'connected', source: 'host', can_connect: true, access_changes_waiting: 2 },
        'calendar',
      ).access_changes_waiting,
    ).toBe(2);
  });
  it('rejects ambiguous role flags, states and counts', () => {
    for (const row of [
      null,
      {},
      { state: 'connected', source: null, can_connect: 'true', can_manage: true },
      { state: 'connected', source: null, can_connect: true, access_changes_waiting: -1 },
    ])
      expect(() => readGoogleConnection(row, 'calendar')).toThrow();
    for (const count of [-1, 1.5, '3', null])
      expect(() => readInboxFetch({ queued: count, skipped: 0, not_for_a_club: 0 })).toThrow();
  });
  it('only navigates to Google authorization URLs', () => {
    const url = 'https://accounts.google.com/o/oauth2/v2/auth?state=synthetic';
    expect(readGoogleAuthorization({ url })).toBe(url);
    for (const url of [
      'javascript:alert(1)',
      'https://accounts.google.com.evil.test/o/oauth2/v2/auth',
      'https://evil.test/',
      'http://accounts.google.com/o/oauth2/auth',
      'https://user@accounts.google.com/o/oauth2/auth',
    ])
      expect(() => readGoogleAuthorization({ url })).toThrow();
  });
  it('returns counts without mail content or assuming undocumented refreshed semantics', () => {
    expect(
      readInboxFetch({
        queued: 2,
        skipped: 1,
        not_for_a_club: 3,
        refreshed: true,
        mail: 'PRIVATE',
      }),
    ).toEqual({ queued: 2, skipped: 1, not_for_a_club: 3 });
  });
});

describe('Google HTTP mutations', () => {
  it('uses CSRF for POST/DELETE and does not treat an ambiguous disconnect as success', async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ url: 'https://accounts.google.com/o/oauth2/v2/auth?state=synthetic' }),
          { headers: { 'Content-Type': 'application/json' } },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', request);
    const api = new ApiClient(httpTransport('/api'), 'http');
    await api.connectGoogle('calendar');
    await api.disconnectGoogle('gmail');
    expect(
      request.mock.calls.map((call) => [
        call[0],
        call[1].method,
        call[1].headers['X-Requested-With'],
      ]),
    ).toEqual([
      ['/api/calendar/connect', 'POST', 'ClubOps'],
      ['/api/inbox/gmail/connect', 'DELETE', 'ClubOps'],
    ]);
    await expect(
      new ApiClient(async () => ({ ok: true }), 'http').disconnectGoogle('calendar'),
    ).rejects.toThrow('not confirmed');
  });
  it('shows only a plain scoped fetch 409; internal errors stay generic', async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Synthetic key expired.' }), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'PRIVATE_ERROR_CANARY' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', request);
    const api = new ApiClient(httpTransport('/api'), 'http');
    await expect(api.fetchInbox()).rejects.toThrow('Synthetic key expired.');
    await expect(api.fetchInbox()).rejects.not.toThrow('PRIVATE_ERROR_CANARY');
  });
});
