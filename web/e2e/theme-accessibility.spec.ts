import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const theme of ['frost', 'afterdark']) {
  test(`${theme} preserves readable actions and content across all screens`, async ({ page }) => {
    test.setTimeout(180_000);
    await page.addInitScript((value) => localStorage.setItem('clubops.theme', value), theme);
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
      '/settings/turnover',
      '/setup',
      '/login',
    ]) {
      await page.goto(route);
      await expect(page.locator('h1, h2').first()).toBeVisible();
      await expect(page.locator('.loading-block')).toHaveCount(0);
      await page.evaluate(() => document.fonts.ready);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),
        route,
      ).toBe(false);
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze();
      failures.push(
        ...results.violations.map((violation) => ({
          route,
          id: violation.id,
          nodes: violation.nodes.slice(0, 8).map((node) => ({
            target: node.target,
            summary: node.failureSummary,
          })),
        })),
      );
    }
    expect(failures).toEqual([]);
  });

  test(`${theme} keeps role sources visible in print`, async ({ page }) => {
    await page.addInitScript((value) => localStorage.setItem('clubops.theme', value), theme);
    await page.goto('/handover');
    await expect(page.locator('.loading-block')).toHaveCount(0);
    const sources = page.locator('.source-chip');
    await expect(sources.first()).toBeVisible();
    const labels = await sources.allTextContents();
    await page.emulateMedia({ media: 'print' });
    await expect(page.getByRole('button', { name: /Switch to .* theme/ })).toBeHidden();
    for (let index = 0; index < labels.length; index++)
      await expect(sources.nth(index)).toBeVisible();
    expect(await sources.allTextContents()).toEqual(labels);
  });

  test(`${theme} keeps review dialogs readable and keyboard focus contained`, async ({ page }) => {
    await page.addInitScript((value) => localStorage.setItem('clubops.theme', value), theme);
    await page.goto('/review');
    const edit = page.getByRole('button', { name: 'Edit then approve' }).first();
    await edit.click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    const box = await dialog.boundingBox();
    expect(box).not.toBeNull();
    const viewport = page.viewportSize()!;
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width);
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height);
    const scan = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(scan.violations).toEqual([]);
    for (let index = 0; index < 12; index++) {
      await page.keyboard.press('Tab');
      expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(
        true,
      );
    }
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
    await expect(edit).toBeFocused();
  });
}
