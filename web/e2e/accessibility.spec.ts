import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('main screens meet automated accessibility checks', async ({ page }) => {
  test.setTimeout(120_000);
  const failures: unknown[] = [];
  for (const route of [
    '/events',
    '/events/ev-sunset-run',
    '/events/new',
    '/chat',
    '/review',
    '/calendar',
    '/inbox',
    '/knowledge',
    '/handover',
    '/settings',
    '/setup',
    '/login',
  ]) {
    await page.goto(route);
    await expect(page.locator('h1, h2').first()).toBeVisible();
    await expect(page.locator('.loading-block')).toHaveCount(0);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    failures.push(
      ...results.violations.map((v) => ({
        route,
        id: v.id,
        impact: v.impact,
        targets: v.nodes.slice(0, 8).map((node) => node.target),
      })),
    );
  }
  expect(failures).toEqual([]);
});
