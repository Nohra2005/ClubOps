/** Synthetic full lifecycle; no Google, real identity transfer or model calls. */
import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { localDate } from '../src/turnover/model';

async function prepare(
  page: Page,
  label = 'Example next term',
  start = localDate(),
  includeTreasurer = false,
) {
  await page.goto('/settings/turnover');
  await page.getByLabel('Term name', { exact: true }).fill(label);
  await page.getByLabel('Starts', { exact: true }).fill(start);
  await page.getByLabel('Ends', { exact: true }).fill(`${Number(start.slice(0, 4)) + 1}-12-31`);
  const first = page.getByRole('group', { name: 'Officer 1', exact: true });
  await first.getByLabel('Name', { exact: true }).fill('Jordan Example');
  await first.getByLabel('Google email', { exact: true }).fill('jordan-next@example.com');
  if (includeTreasurer) {
    await page.getByRole('button', { name: 'Add officer', exact: true }).click();
    const second = page.getByRole('group', { name: 'Officer 2', exact: true });
    await second.getByLabel('Name', { exact: true }).fill('Taylor Incoming');
    await second.getByLabel('Google email', { exact: true }).fill('taylor-next@example.com');
    await second.getByRole('combobox', { name: 'Role', exact: true }).selectOption('treasurer');
  }
  if (includeTreasurer) {
    const scan = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(scan.violations).toEqual([]);
    await page.screenshot({
      path: `../../c39-visual/prepare-${test.info().project.name}.png`,
      fullPage: true,
    });
  }
  await page.getByRole('button', { name: 'Save and review', exact: true }).click();
  await expect(page.getByRole('heading', { name: label, exact: true })).toBeVisible();
}
async function ready(page: Page) {
  await page
    .getByRole('checkbox', {
      name: 'I reviewed the incoming cabinet, vacancies and outstanding work.',
    })
    .check();
  await page.getByRole('button', { name: 'Mark ready', exact: true }).click();
  await expect(page.getByText('Ready to activate', { exact: true })).toBeVisible();
}
async function confirm(page: Page, label = 'Example next term') {
  await page.getByRole('button', { name: 'Activate demo term', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Activate this cabinet?' });
  await dialog.getByLabel('Type the term name to confirm').fill(label);
  await dialog.getByRole('button', { name: 'Confirm activation', exact: true }).click();
}

test('turnover replaces the cabinet once, preserves history and introduces each officer once', async ({
  page,
}, testInfo) => {
  testInfo.setTimeout(60_000);
  const requests: string[] = [];
  await page.route('**/api/**', (route) => {
    if (!new URL(route.request().url()).pathname.startsWith('/api/')) return route.fallback();
    requests.push(route.request().url());
    return route.abort();
  });
  await page.goto('/events');
  await expect(page.getByRole('region', { name: 'Start your role' })).toHaveCount(0);
  await prepare(page, 'Example next term', localDate(), true);
  await expect(page.getByRole('region', { name: 'Work to carry forward' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Mark ready' })).toBeDisabled();
  await ready(page);
  await page.reload();
  await expect(page.getByText('Ready to activate', { exact: true })).toBeVisible();
  await page.screenshot({
    path: `../../c39-visual/review-${testInfo.project.name}.png`,
    fullPage: true,
  });
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(axe.violations).toEqual([]);
  await page.getByRole('button', { name: 'Activate demo term' }).click();
  const dialog = page.getByRole('dialog', { name: 'Activate this cabinet?' });
  await expect(dialog.getByRole('button', { name: 'Confirm activation' })).toBeDisabled();
  await dialog.getByRole('button', { name: 'Keep working' }).click();
  await expect(page.getByRole('heading', { name: /^Active term:/ })).toHaveCount(0);
  await confirm(page);
  await expect(
    page.getByRole('heading', { name: 'Active term: Example next term', exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Activate demo term' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Save and review' })).toHaveCount(0);
  await page.getByText('Previous cabinet', { exact: true }).click();
  await expect(page.locator('.turnover-roster')).toHaveCount(2);
  await page.getByRole('link', { name: 'Open workspace', exact: true }).click();
  const arrival = page.getByRole('region', { name: 'Your new cabinet term' });
  await expect(arrival).toContainText('Example next term');
  await expect(arrival).toContainText('president');
  await expect(page.locator('.event-card').first()).toBeVisible();
  await page.screenshot({
    path: `../../c39-visual/arrival-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await arrival.getByRole('button', { name: 'Start this term', exact: true }).click();
  await expect(arrival).toHaveCount(0);
  await page.reload();
  await expect(arrival).toHaveCount(0);
  await page.locator('.user-menu > summary').click();
  await page.getByLabel('Preview role').selectOption('treasurer');
  await expect(arrival).toBeVisible();
  await expect(arrival).toContainText('treasurer');
  await arrival.getByRole('button', { name: 'Start this term', exact: true }).click();
  await expect(arrival).toHaveCount(0);
  if (!(await page.getByLabel('Preview role').isVisible()))
    await page.locator('.user-menu > summary').click();
  await page.getByLabel('Preview role').selectOption('president');
  await expect(arrival).toHaveCount(0);
  await page.goto('/settings#cabinet');
  await expect(
    page.locator('.cabinet-row').getByText('Jordan Example', { exact: true }),
  ).toBeVisible();
  await page.goto('/chat');
  await expect(page.getByText(/Help me learn my/)).toHaveCount(0);
  await expect(page.getByText('See the context included with my question')).toHaveCount(0);
  expect(requests).toEqual([]);
  await expect(page.locator('body')).toHaveJSProperty(
    'scrollWidth',
    await page.locator('body').evaluate((element) => element.clientWidth),
  );
});

test('future dates do not activate and editing a reviewed draft requires a fresh review', async ({
  page,
}) => {
  await prepare(page, 'Future example', `${new Date().getFullYear() + 1}-01-01`);
  await ready(page);
  await expect(page.getByRole('button', { name: 'Activate demo term' })).toBeDisabled();
  await page.getByRole('button', { name: 'Edit draft' }).click();
  await page.getByLabel('Term name', { exact: true }).fill('Revised future example');
  await page.getByRole('button', { name: 'Save and review' }).click();
  await expect(page.getByRole('button', { name: 'Mark ready' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Activate demo term' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Cancel turnover' }).click();
  const dialog = page.getByRole('dialog', { name: 'Cancel this turnover?' });
  await dialog.getByRole('button', { name: 'Confirm cancellation' }).click();
  await expect(page.getByLabel('Term name', { exact: true })).toHaveValue('');
  await expect(page.getByRole('heading', { name: /^Active term:/ })).toHaveCount(0);
});

test('F-507: changed source knowledge blocks activation until the draft is reviewed again', async ({
  page,
}) => {
  await prepare(page);
  await ready(page);
  await page.evaluate(() => {
    const key = 'clubops.demo.workspace.v1.running-club';
    const workspace = JSON.parse(localStorage.getItem(key)!);
    workspace.knowledge[0].statement += ' Synthetic source changed after review.';
    localStorage.setItem(key, JSON.stringify(workspace));
  });
  await page.reload();
  await confirm(page);
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText(
    'Work or cabinet changed',
  );
  await expect(page.getByRole('heading', { name: /^Active term:/ })).toHaveCount(0);
});

test('denied browser persistence leaves the sample turnover usable in this tab', async ({
  page,
}) => {
  await page.addInitScript(() => {
    Storage.prototype.setItem = () => {
      throw new DOMException('Synthetic storage denied');
    };
  });
  await prepare(page);
  await ready(page);
  await confirm(page);
  await expect(
    page.getByRole('heading', { name: 'Active term: Example next term', exact: true }),
  ).toBeVisible();
  await expect(page.locator('.toast[role="status"]')).toContainText(
    'Changes stay in this tab only',
  );
});
