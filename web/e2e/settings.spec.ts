import { expect, test } from '@playwright/test';

test('settings adds cabinet members and queues uploaded documents for review', async ({ page }) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Add member', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill('Casey Demo');
  await page.getByLabel('Email', { exact: true }).fill('casey@example.com');
  await page.getByRole('dialog').getByRole('button', { name: 'Add member', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.cabinet-list')).toContainText('Casey Demo');
  await page.getByLabel('Upload source document').setInputFiles({ name: 'synthetic-handbook.txt', mimeType: 'text/plain', buffer: Buffer.from('Synthetic example document. Not an AUB policy.') });
  await expect(page.locator('.document-row').filter({ hasText: 'synthetic-handbook.txt' })).toBeVisible();
  await page.goto('/review');
  await expect(page.locator('.review-statement').filter({ hasText: 'synthetic-handbook.txt' })).toBeVisible();
});
