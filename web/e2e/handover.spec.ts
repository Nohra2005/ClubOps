import { expect, test } from '@playwright/test';

test('role reference exports sources without implying cabinet activation', async ({ page }) => {
  await page.goto('/handover');
  await expect(page.getByRole('heading', { name: 'Role reference', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Sign off|Activate/ })).toHaveCount(0);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download text', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('running-club-president-handover.txt');
  await page.getByLabel('Guide for').selectOption('treasurer');
  await expect(page.getByRole('button', { name: 'Download text', exact: true })).toBeEnabled();
});
