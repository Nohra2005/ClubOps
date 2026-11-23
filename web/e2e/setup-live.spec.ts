/** Production app factory, HTTP cookies and SQLite; synthetic accounts, no route interception. */
import { expect, test } from '@playwright/test';

const csrf = { 'X-Requested-With': 'ClubOps' };

test('new-club setup resumes saved progress, completes with skips and leaves Review empty', async ({
  page,
  context,
}, testInfo) => {
  const login = await context.request.post('/api/auth/dev', {
    headers: csrf,
    data: { email: `setup-${testInfo.project.name}@example.com` },
  });
  expect(login.status()).toBe(200);
  const before = await context.request.get('/api/me');
  expect((await before.json()).club.setup_complete).toBe(false);

  await page.goto('/events');
  await expect(page).toHaveURL(/\/setup$/);
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await expect(page.getByText('1 of 10', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Skip this question', exact: true }).click();
  await expect(page.getByText('2 of 10', { exact: true })).toBeVisible();
  const secondQuestion = await page.locator('.setup-question h2').innerText();

  await page.getByRole('button', { name: /Stop for now/ }).click();
  await expect(page).toHaveURL(/\/events$/);
  await page.reload();
  await expect(page).toHaveURL(/\/events$/);

  // Missing CSRF must neither advance durable progress nor extract facts.
  const denied = await context.request.post('/api/setup/next', { data: { answer: '[skip]' } });
  expect(denied.status()).toBe(403);
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await expect(page.getByText('2 of 10', { exact: true })).toBeVisible();
  await expect(page.locator('.setup-question h2')).toHaveText(secondQuestion);

  for (let index = 2; index <= 10; index++) {
    await expect(page.getByText(`${index} of 10`, { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Skip this question', exact: true }).click();
  }
  await expect(
    page.getByRole('heading', { name: 'Your club interview is complete.' }),
  ).toBeVisible();
  await expect(page.getByText('0 of 4 starter steps recorded on this browser')).toBeVisible();
  const after = await context.request.get('/api/me');
  expect((await after.json()).club.setup_complete).toBe(true);

  // Reopening reads server progress; browser-local checklist ticks are a separate concern.
  await page.reload();
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await expect(
    page.getByRole('heading', { name: 'Your club interview is complete.' }),
  ).toBeVisible();
  await expect(page.getByText('0 of 4 starter steps recorded on this browser')).toBeVisible();
  const review = await context.request.get('/api/review');
  expect(review.ok()).toBe(true);
  expect(await review.json()).toEqual([]);
});

test('a real adviser session cannot advance a new club interview', async ({
  page,
  context,
}, testInfo) => {
  const login = await context.request.post('/api/auth/dev', {
    headers: csrf,
    data: { email: `setup-${testInfo.project.name}-adviser@example.com` },
  });
  expect(login.status()).toBe(200);
  const denied = await context.request.post('/api/setup/next', {
    headers: csrf,
    data: { answer: '[skip]' },
  });
  expect(denied.status()).toBe(403);
  await page.goto('/setup');
  await expect(page).toHaveURL(/\/events$/);
  await expect(page.getByRole('button', { name: 'Start or resume club setup' })).toHaveCount(0);
});
