import { expect, test } from '@playwright/test';

test('knowledge edits go to review without overwriting the approved fact', async ({ page }) => {
  await page.goto('/knowledge?tab=tips');
  await page.getByLabel('Search approved knowledge').fill('Cedar');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.getByRole('link', { name: 'Give Cedar Coffee ten days', exact: true }).click();
  await page.getByRole('button', { name: 'Suggest an edit' }).click();
  await page
    .getByLabel('Suggested statement')
    .fill('Synthetic change: confirm the sponsor lead time again.');
  await page.getByRole('button', { name: 'Send to Review' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.fact-statement')).toContainText('ten days');
  await expect(page.locator('.fact-statement')).not.toContainText('Synthetic change');
  await page.goto('/review');
  await expect(
    page.locator('.review-statement').filter({ hasText: 'Synthetic change:' }),
  ).toBeVisible();
});
