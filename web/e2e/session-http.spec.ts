/** Synthetic /api/me responses through the real HTTP adapter; no provider or backend writes. */
import { expect, test } from '@playwright/test';
import { clubs, createWorkspace } from '../src/api/fixtures';

const workspace = createWorkspace('running-club');
const valid = {
  user: workspace.members[0],
  role: 'president',
  club: clubs[0],
  counts: { overdue_events: 0, review: 0, reminders: 0 },
};

for (const [name, invalid] of [
  ['unknown role', { ...valid, role: 'PRIVATE_ROLE_CANARY' }],
  [
    'malformed member',
    { ...valid, user: { ...valid.user, name: { PRIVATE_MEMBER_CANARY: 'synthetic' } } },
  ],
  ['non-boolean setup', { ...valid, club: { ...valid.club, setup_complete: 'false' } }],
  ['invalid counts', { ...valid, counts: { ...valid.counts, review: -1 } }],
] as const) {
  test(`HTTP session rejects ${name} before opening the protected workspace`, async ({ page }) => {
    const protectedRequests: string[] = [];
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text());
    });
    await page.route('**/api/**', (route) => {
      const path = new URL(route.request().url()).pathname;
      if (!path.startsWith('/api/')) return route.fallback();
      if (path === '/api/me') return route.fulfill({ json: invalid });
      protectedRequests.push(`${route.request().method()} ${path}`);
      return route.fulfill({ status: 403, json: { detail: 'Synthetic refusal' } });
    });
    await page.goto('/events');
    await expect(
      page.getByRole('heading', { name: "Let's get you connected.", exact: true }),
    ).toBeVisible();
    await expect(page.getByRole('alert')).toContainText('could not confirm your workspace');
    await expect(page.getByRole('button', { name: 'Try again', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toBeVisible();
    await expect(page.locator('.app-shell')).toHaveCount(0);
    await expect(page.getByText("This page couldn't open.", { exact: true })).toHaveCount(0);
    await expect(page.locator('body')).not.toContainText('PRIVATE_');
    expect(protectedRequests).toEqual([]);
    expect(errors.join('\n')).not.toContain('PRIVATE_');
  });
}

test('HTTP session retry rechecks the server and opens only a valid workspace without writes', async ({
  page,
}) => {
  let invalid = true;
  let meCalls = 0;
  const calls: string[] = [];
  await page.route('**/api/**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith('/api/')) return route.fallback();
    calls.push(`${route.request().method()} ${path}`);
    if (path === '/api/me') {
      meCalls++;
      return route.fulfill({ json: invalid ? { ...valid, role: 'unknown' } : valid });
    }
    return route.fulfill({ json: [] });
  });
  await page.goto('/events');
  await expect(page.getByRole('alert')).toContainText('could not confirm your workspace');
  expect(calls.every((call) => call === 'GET /api/me')).toBe(true);
  const before = meCalls;
  invalid = false;
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Events', exact: true })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(meCalls).toBe(before + 1);
  expect(calls.some((call) => call === 'GET /api/events')).toBe(true);
  expect(calls.every((call) => ['GET /api/me', 'GET /api/events'].includes(call))).toBe(true);
});

test('HTTP session retains the published active adviser role and hides planning controls', async ({
  page,
}) => {
  const writes: string[] = [];
  await page.route('**/api/**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith('/api/')) return route.fallback();
    if (route.request().method() !== 'GET') writes.push(`${route.request().method()} ${path}`);
    return route.fulfill({ json: path === '/api/me' ? { ...valid, role: 'adviser' } : [] });
  });
  await page.goto('/events');
  await expect(page.getByRole('heading', { name: 'Events', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Plan an event', exact: true })).toHaveCount(0);
  await expect(page.getByRole('link', { name: "Let's plan something", exact: true })).toHaveCount(
    0,
  );
  expect(writes).toEqual([]);
});
