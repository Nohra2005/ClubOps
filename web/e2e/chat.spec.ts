import { expect, test } from '@playwright/test';

test('chat shows sources, admits uncertainty and queues teaching for review', async ({ page }) => {
  await page.goto('/chat');
  await page
    .getByLabel('Ask your club', { exact: true })
    .fill('What did we learn from the last run?');
  await page.getByRole('button', { name: 'Ask ClubOps' }).click();
  await expect(page.locator('.source-list')).toContainText('Welcome run debrief');
  await page.getByLabel('Ask your club', { exact: true }).fill('Who handles open-water insurance?');
  await page.getByRole('button', { name: 'Ask ClubOps' }).click();
  await expect(page.getByText("I don't know this yet.", { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Teach the club', exact: true }).click();
  await page
    .getByLabel('Teach your club', { exact: true })
    .fill('Synthetic lesson: carry spare water cups.');
  await page.getByRole('button', { name: 'Send fact for review' }).click();
  await expect(page.getByText('New fact sent for review', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText('New fact sent for review', { exact: true })).toBeVisible();
  await page.getByLabel('Club', { exact: true }).selectOption('asme');
  await page.goto('/chat');
  await expect(page.getByRole('heading', { name: 'What would you like to know?' })).toBeVisible();
  await expect(
    page.getByText('Synthetic lesson: carry spare water cups.', { exact: true }),
  ).toHaveCount(0);
});
