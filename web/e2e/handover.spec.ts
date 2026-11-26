import { expect, test } from '@playwright/test';

test('handover exports a sourced guide and requires explicit sign-off', async ({ page }) => {
  await page.goto('/handover');
  await expect(page.getByRole('button', { name: 'Sign off handover', exact: true })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download text', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('running-club-president-handover.txt');
  await page.getByRole('button', { name: 'Sign off handover', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm sign-off', exact: true }).click();
  await expect(page.getByText('Signed off by Alex Morgan', { exact: true })).toBeVisible();
  await page.getByLabel('Guide for').selectOption('treasurer');
  await expect(page.getByRole('button', { name: 'Sign off handover', exact: true })).toBeVisible();
});
