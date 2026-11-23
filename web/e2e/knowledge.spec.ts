import { expect, test } from '@playwright/test';

test('a cabinet member edits a fact at once and can undo the change', async ({ page }) => {
  await page.goto('/knowledge?tab=tips');
  await page.getByLabel('Search approved knowledge').fill('Cedar');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.getByRole('link', { name: 'Give Cedar Coffee ten days', exact: true }).click();
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  await page.getByLabel('Statement').fill('Synthetic change: confirm the sponsor lead time again.');
  await page.getByRole('button', { name: 'Save change' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.fact-statement')).toContainText('Synthetic change');
  await page.getByRole('button', { name: 'Undo last change' }).click();
  await expect(page.locator('.fact-statement')).toContainText('ten days');
});
