import { expect, test } from '@playwright/test';

test('production serves deep links, keeps API errors as JSON, and never rewrites missing assets', async ({
  request,
}) => {
  const deepLink = await request.get('/events/new');
  expect(deepLink.status()).toBe(200);
  expect(deepLink.headers()['content-type']).toContain('text/html');
  expect(await deepLink.text()).toContain('<div id="root">');
  const privateAPI = await request.get('/api/me');
  expect(privateAPI.status()).toBe(401);
  expect(privateAPI.headers()['cache-control']).toBe('no-store');
  const missingAPI = await request.get('/api/does-not-exist');
  expect(missingAPI.status()).toBe(404);
  expect(missingAPI.headers()['content-type']).toContain('application/json');
  const missingAsset = await request.get('/assets/does-not-exist.js');
  expect(missingAsset.status()).toBe(404);
  expect(await missingAsset.text()).not.toContain('<div id="root">');
});
