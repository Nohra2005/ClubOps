import { expect, test } from '@playwright/test';

test('calendar handles club-wide reminders and month navigation without overflow', async ({
  page,
}) => {
  await page.goto('/calendar');
  await page.getByRole('button', { name: 'Check the current OSA documents, 1 Oct' }).click();
  await expect(
    page.getByText('A club-wide reminder. It is not attached to an event.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Mark done', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Mark not done', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await page.getByRole('button', { name: 'Next month', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'November 2026' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
