import { expect, test } from '@playwright/test';

test('local development sign-in rejects unknown emails and uses a real cabinet cookie', async ({
  page,
  context,
}) => {
  await page.goto('/login');
  await expect(page.getByText('Local development only. Use a cabinet test account.')).toBeVisible();
  await page.getByLabel('Development email').fill('not-in-cabinet@example.com');
  await page.getByRole('button', { name: 'Sign in locally', exact: true }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Development email').fill('president@example.com');
  await page.getByRole('button', { name: 'Sign in locally', exact: true }).click();
  await expect(page).toHaveURL(/\/events$/);
  expect((await context.request.get('/api/me')).status()).toBe(200);
  expect((await context.cookies()).some((cookie) => cookie.httpOnly)).toBe(true);
});
