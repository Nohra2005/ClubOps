import { expect, test } from '@playwright/test';

test('opens shareable routes and fits the phone viewport', async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  for (const route of [
    '/events',
    '/chat',
    '/review',
    '/calendar',
    '/knowledge',
    '/handover',
    '/settings',
  ]) {
    await page.goto(route);
    await expect(page.locator('main h1')).toBeVisible();
    await expect(page.locator('.loading-block')).toHaveCount(0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    if (route === '/events')
      await page.screenshot({
        path: `test-results/shell-${testInfo.project.name}.png`,
        fullPage: true,
      });
  }
  expect(errors).toEqual([]);
});

test('switching clubs clears the visible workspace identity', async ({ page }) => {
  await page.goto('/events');
  await page.getByLabel('Club', { exact: true }).selectOption('asme');
  await expect(page.getByLabel('Club', { exact: true })).toHaveValue('asme');
  await page.locator('.user-menu > summary').click();
  await expect(page.locator('.user-menu .popover-panel')).toContainText('ASME');
});
