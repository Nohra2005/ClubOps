import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiClient, httpTransport } from './client';

afterEach(() => vi.unstubAllGlobals());
describe('real API boundary', () => {
  it('explains unimplemented server features without claiming a successful save', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('Not implemented', { status: 501 })),
    );
    await expect(
      new ApiClient(httpTransport(), 'http').teach('A synthetic proposed fact'),
    ).rejects.toMatchObject({
      status: 501,
      message: expect.stringContaining('not connected to the server yet'),
    });
  });
  it('continues the existing backend run through its published endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          run_id: 'run-example',
          club_id: 'running-club',
          event_id: null,
          status: 'running',
          steps: [],
          steps_used: 0,
          step_limit: 8,
          cost_usd: '0',
          cost_limit_usd: '0.05',
        }),
        { headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetcher);
    const api = new ApiClient(httpTransport(), 'http');
    await expect(api.continueRun('run-example')).resolves.toEqual({ run_id: 'run-example' });
    expect(fetcher.mock.calls[0][0]).toBe('/api/runs/run-example/continue');
    expect(fetcher.mock.calls[0][1].method).toBe('POST');
    await expect(api.stopRun('run-example')).rejects.toMatchObject({ status: 501 });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('sends CSRF headers on bodiless changes and uploads while the browser sets multipart boundaries', async () => {
    const fetcher = vi.fn().mockImplementation(async () => new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetcher);
    const transport = httpTransport();
    await transport('/events/ev-example/rebuild', { method: 'POST' });
    const upload = new FormData();
    upload.append('file', new File(['Synthetic document'], 'example.txt'));
    await transport('/documents', { method: 'POST', body: upload });
    await transport('/cabinet', { method: 'DELETE', body: { member_id: 'm-example' } });
    await transport('/events');
    for (const [, request] of fetcher.mock.calls.slice(0, 3)) {
      expect(new Headers(request.headers).get('X-Requested-With')).toBe('ClubOps');
      expect(request.credentials).toBe('include');
    }
    expect(new Headers(fetcher.mock.calls[0][1].headers).has('Content-Type')).toBe(false);
    expect(new Headers(fetcher.mock.calls[1][1].headers).has('Content-Type')).toBe(false);
    expect(fetcher.mock.calls[1][1].body).toBe(upload);
    expect(new Headers(fetcher.mock.calls[2][1].headers).get('Content-Type')).toBe(
      'application/json',
    );
    expect(new Headers(fetcher.mock.calls[3][1].headers).has('X-Requested-With')).toBe(false);
  });
  it('uses credentials and encodes identifiers without simulating production writes', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ task_id: 'ev-example/task' }), {
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetcher);
    const api = new ApiClient(httpTransport('/api'), 'http');
    await api.task('ev-example/task', { state: 'done' });
    expect(fetcher.mock.calls[0][0]).toBe('/api/tasks/ev-example%2Ftask');
    expect(fetcher.mock.calls[0][1]).toMatchObject({
      credentials: 'include',
      method: 'PATCH',
      body: '{"state":"done"}',
    });
    await expect(api.google(true)).rejects.toMatchObject({ status: 501 });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('rejects HTML instead of treating a login page as saved application data', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response('<html>Sign in</html>', { headers: { 'Content-Type': 'text/html' } }),
        ),
    );
    await expect(new ApiClient(httpTransport(), 'http').events()).rejects.toMatchObject({
      status: 502,
    });
  });
  it('keeps server errors generic and reports loss of connection', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response('secret upstream details', { status: 500 }))
      .mockRejectedValueOnce(new TypeError('socket failed'));
    vi.stubGlobal('fetch', fetcher);
    const api = new ApiClient(httpTransport(), 'http');
    await expect(api.events()).rejects.toThrow('Your edits are still on this page');
    await expect(api.events()).rejects.toThrow("Can't reach ClubOps");
  });
});
