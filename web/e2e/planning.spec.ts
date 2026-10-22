import { expect, test } from '@playwright/test';

test('requires human detail confirmation and pauses for an agent question', async ({ page }) => {
  await page.goto('/events/new');
  await page
    .getByLabel('Describe your event')
    .fill('A friendly campus run with coffee next Thursday');
  await page.getByRole('button', { name: 'Plan it', exact: true }).click();
  await expect(page.getByRole('heading', { name: "Let's check the details." })).toBeVisible();
  await page.getByRole('spinbutton', { name: /Budget/ }).fill('0');
  await page.getByRole('checkbox', { name: /I checked the details/ }).check();
  await page.getByRole('button', { name: 'Confirm details', exact: true }).click();
  await expect(page.getByPlaceholder('Your answer')).toBeVisible();
  await expect(page.locator('.agent-question')).toContainText('Will there be prizes?');
  const runs = await page.evaluate(() =>
    Object.keys(JSON.parse(localStorage.getItem('clubops.demo.workspace.v1.running-club')!).runs),
  );
  expect(runs).toHaveLength(1);
  await page.getByPlaceholder('Your answer').fill('No');
  await page.getByRole('button', { name: 'Answer and continue' }).click();
  await expect(page.getByRole('button', { name: 'Approve plan', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Approve plan', exact: true }).click();
  await expect(page.getByText('Approved by Alex Morgan', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText('Approved by Alex Morgan', { exact: true })).toBeVisible();
});
