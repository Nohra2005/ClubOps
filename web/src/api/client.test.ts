import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiClient, httpTransport } from './client';

afterEach(() => vi.unstubAllGlobals());
describe('real API boundary', () => {
  it('uses credentials and encodes identifiers without simulating production writes', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ task_id: 'ev-example/task' }),{ headers: { 'Content-Type': 'application/json' } })); vi.stubGlobal('fetch',fetcher);
    const api = new ApiClient(httpTransport('/api'),'http'); await api.task('ev-example/task',{ state: 'done' });
    expect(fetcher.mock.calls[0][0]).toBe('/api/tasks/ev-example%2Ftask');
    expect(fetcher.mock.calls[0][1]).toMatchObject({ credentials: 'include',method: 'PATCH',body: '{"state":"done"}' });
    await expect(api.google(true)).rejects.toMatchObject({ status: 501 }); expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('rejects HTML instead of treating a login page as saved application data', async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html>Sign in</html>',{ headers: { 'Content-Type': 'text/html' } })));
    await expect(new ApiClient(httpTransport(),'http').events()).rejects.toMatchObject({ status: 502 });
  });
  it('keeps server errors generic and reports loss of connection', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response('secret upstream details',{ status: 500 })).mockRejectedValueOnce(new TypeError('socket failed')); vi.stubGlobal('fetch',fetcher);
    const api = new ApiClient(httpTransport(),'http'); await expect(api.events()).rejects.toThrow('Your edits are still on this page');
    await expect(api.events()).rejects.toThrow("Can't reach ClubOps");
  });
});
