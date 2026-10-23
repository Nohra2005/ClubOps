import { expect, test } from '@playwright/test';

test('new-club setup is skippable and leaves learned facts unapproved', async ({ page }) => {
  await page.goto('/events');
  await page.getByLabel('Club', { exact: true }).selectOption('asme');
  await expect(page).toHaveURL(/\/setup$/);
  await page.getByRole('button', { name: 'Start club setup' }).click();
  await page.getByLabel('Your setup answer').fill('Synthetic club: monthly design workshops.');
  await page.getByRole('button', { name: 'Next question', exact: true }).click();
  for (let i = 0; i < 9; i++)
    await page.getByRole('button', { name: 'Skip this question', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your club is ready to start.' })).toBeVisible();
  await expect(page.locator('.setup-proposals')).toContainText('monthly design workshops');
  const workspace = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('clubops.demo.workspace.v1.asme')!),
  );
  expect(
    workspace.review.some(
      (r: { status: string; statement: string }) =>
        r.status === 'pending' && r.statement.includes('monthly design workshops'),
    ),
  ).toBe(true);
  expect(
    workspace.knowledge.some((r: { statement: string }) =>
      r.statement.includes('monthly design workshops'),
    ),
  ).toBe(false);
});
