/** Real local API, cookies, SQLite and planner; synthetic people and scripted model, no interceptions. */
import { expect, test } from '@playwright/test';

test('plans through the real API, requires approval, and retains the approved revision', async ({
  page,
  context,
}) => {
  const signedIn = await context.request.post('/api/auth/dev', {
    headers: { 'X-Requested-With': 'ClubOps' },
    data: { email: 'president@example.com' },
  });
  expect(signedIn.ok()).toBe(true);
  await page.goto('/events/new');
  await page.getByLabel('Describe your event').fill('Synthetic campus fun run on Green Field');
  await page.getByRole('button', { name: 'Plan it', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Campus fun run', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve plan', exact: true })).toBeVisible();
  const eventId = new URL(page.url()).pathname.split('/').at(-1)!;
  const before = await context.request.get('/api/calendar?month=2026-11');
  expect(
    (await before.json()).items.some((item: { event_id: string }) => item.event_id === eventId),
  ).toBe(false);
  await page.getByRole('button', { name: 'Approve plan', exact: true }).click();
  await expect(page.getByText('Approved by Synthetic President', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText('Approved by Synthetic President', { exact: true })).toBeVisible();
  const after = await context.request.get('/api/calendar?month=2026-11');
  expect(
    (await after.json()).items.some((item: { event_id: string }) => item.event_id === eventId),
  ).toBe(true);
  await page.goto('/handover');
  await expect(page.getByRole('heading', { name: 'Handover', exact: true })).toBeVisible();
  await expect(page.getByText("What we don't know yet", { exact: true })).toBeVisible();
  const guideResponse = page.waitForResponse('**/api/handover/events');
  await page.getByRole('combobox', { name: /Guide for/ }).selectOption('events');
  expect((await guideResponse).ok()).toBe(true);
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.goto('/settings');
  await expect(page.getByText('Planner steps', { exact: true })).toBeVisible();
  await expect(page.getByText('Cost per successful recorded plan', { exact: true })).toBeVisible();
  await page.getByLabel('Your account', { exact: true }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await context.request.get('/api/me')).status()).toBe(401);
});
