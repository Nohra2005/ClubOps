import { expect, test } from '@playwright/test';

test('batch review excludes rules and records review timing', async ({ page }) => {
  await page.goto('/review');
  await page.getByRole('button', { name: 'Approve all facts', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Head count before the run' })).toHaveCount(0);
  const rule = page.locator('#review-rule');
  await expect(rule).toBeVisible();
  await rule.getByRole('button', { name: 'Approve', exact: true }).click();
  await expect(rule).toContainText('Waiting for 2nd president');
  const reviewed = await page.evaluate(() => JSON.parse(localStorage.getItem('clubops.demo.workspace.v1.running-club')!).review.find((r: { id: string }) => r.id === 'review-coffee'));
  expect(reviewed.opened_at).toBeTruthy(); expect(reviewed.decided_at).toBeTruthy(); expect(reviewed.status).toBe('approved');
  await page.reload(); await expect(page.locator('#review-rule')).toContainText('Waiting for 2nd president');
});
