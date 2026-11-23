import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('forwarding requires a sample proof and makes no requests or persistent address records', async ({
  page,
}, testInfo) => {
  const requests: string[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api')) requests.push(request.url());
  });
  await page.goto('/settings');
  const panel = page.getByRole('region', { name: 'Forwarding setup' });
  await panel.getByLabel('Demo connection state').selectOption('connected');
  await panel.getByLabel('Demo reader access').selectOption('failed');
  await expect(panel).toContainText('Shared-calendar reader access: failed');
  await panel.getByLabel('Sample sending address').fill('member@example.com');
  await panel.getByRole('button', { name: 'Start sample verification' }).click();
  await expect(panel).toContainText('Sample address status: pending');
  await panel.getByLabel('Sample verification code').fill('WRONG');
  await panel.getByRole('button', { name: 'Simulate received code' }).click();
  await expect(panel.getByRole('alert')).toContainText('does not match');
  await panel.getByRole('button', { name: 'Simulate code expiry' }).click();
  await expect(panel).toContainText('Sample address status: expired');
  await panel.getByRole('button', { name: 'Start sample verification' }).click();
  await panel.getByLabel('Sample verification code').fill('DEMO-4821');
  await panel.getByRole('button', { name: 'Simulate received code' }).click();
  await expect(panel).toContainText('Sample address status: verified');
  await panel.getByRole('button', { name: 'Test my forwarding', exact: true }).click();
  await panel.getByRole('button', { name: 'Simulate test failure' }).click();
  await expect(panel).toContainText('Forwarding test: failed');
  await panel.getByRole('button', { name: 'Test my forwarding', exact: true }).click();
  await panel.getByRole('button', { name: 'Simulate test received' }).click();
  await expect(panel).toContainText('Forwarding test: passed');
  expect((await new AxeBuilder({ page }).include('#forwarding').analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await panel.screenshot({ path: `test-results/forwarding-${testInfo.project.name}.png` });
  expect(requests).toEqual([]);
  const saved = await page.evaluate(() => Object.values(localStorage).join('\n'));
  expect(saved).not.toContain('member@example.com');
  expect(saved).not.toContain('DEMO-4821');
  await page.reload();
  await expect(panel).toContainText('Sample address status: none');
});

test('cancel and partial-read retry preserve successful and skipped mail', async ({ page }) => {
  await page.goto('/settings');
  await page.getByLabel('Demo connection state').selectOption('connected');
  await page.getByRole('link', { name: 'Open waiting email' }).click();
  await page.getByText('Demo read outcomes', { exact: true }).click();
  await page.getByLabel('Next simulated read result').selectOption('partial');
  await page.getByRole('button', { name: 'Read waiting email · costs money', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Waiting email' })).toContainText(
    '0 sample facts proposed',
  );
  await page.getByRole('button', { name: 'Read waiting email · costs money', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm simulated read' }).click();
  await expect(page.getByRole('region', { name: 'Waiting email' })).toContainText(
    '1 read · 1 failed · 1 sample facts proposed',
  );
  await expect(page.getByRole('article', { name: 'Synthetic non-OSA forward' })).toContainText(
    'ClubOps only reads e-mails forwarded from OSA staff.',
  );
  await expect(
    page.getByRole('article', { name: 'Synthetic non-OSA forward' }).getByRole('button'),
  ).toHaveCount(0);
  await page.getByLabel('Next simulated read result').selectOption('success');
  await page.getByRole('button', { name: 'Retry this read · costs money' }).click();
  await page.getByRole('button', { name: 'Confirm simulated read' }).click();
  await expect(page.getByRole('region', { name: 'Waiting email' })).toContainText(
    '2 read · 0 failed · 2 sample facts proposed',
  );
  await expect(page.getByRole('button', { name: /Read this|Read waiting|Retry this/ })).toHaveCount(
    0,
  );
});

test('all connection states remain distinct and expired access blocks reads', async ({ page }) => {
  await page.goto('/settings');
  const panel = page.getByRole('region', { name: 'Forwarding setup' });
  for (const state of ['disconnected', 'pending', 'connected', 'expired', 'failed']) {
    await panel.getByLabel('Demo connection state').selectOption(state);
    await expect(panel.getByLabel('Demo connection state')).toHaveValue(state);
  }
  await panel.getByLabel('Demo connection state').selectOption('expired');
  await expect(panel).toContainText('The president needs to reconnect');
  await page.getByRole('link', { name: 'Open waiting email' }).click();
  await expect(
    page.getByRole('button', { name: 'Read waiting email · costs money', exact: true }),
  ).toBeDisabled();
});

test('sample deadline defaults to calendar and expires into a reversible archive without approving shared rules', async ({
  page,
}) => {
  await page.goto('/review');
  const panel = page.getByRole('region', { name: 'Deadline lifecycle preview' });
  const card = panel.getByRole('article', { name: 'Sample deadline card' });
  await expect(card.getByRole('checkbox')).toBeChecked();
  await card.getByLabel('Card audience').selectOption('shared');
  await expect(card.getByRole('button', { name: 'Approve sample deadline' })).toBeDisabled();
  await card.getByLabel('Card audience').selectOption('club');
  await card.getByLabel('Expiry date', { exact: true }).fill('2026-11-01');
  await card.getByRole('button', { name: 'Approve sample deadline' }).click();
  await expect(card).toHaveCount(0);
  await panel.getByRole('button', { name: 'Archive samples', exact: true }).click();
  const archived = panel
    .getByRole('article', { name: 'Archived sample deadline' })
    .filter({ hasText: 'send the room request' });
  await archived.getByRole('button', { name: 'Restore sample' }).click();
  await expect(panel.getByRole('alert')).toContainText('future expiry');
  await archived.getByLabel('New expiry for Restore').fill('2026-12-01');
  await archived.getByRole('button', { name: 'Restore sample' }).click();
  await panel.getByRole('button', { name: 'Active samples', exact: true }).click();
  await expect(card).toContainText('Expiry: 2026-12-01');
  await expect(card).toContainText('No Google event was created');
});

test('adviser previews are read only and new panels fit and pass accessibility checks', async ({
  page,
}, testInfo) => {
  await page.addInitScript(() =>
    localStorage.setItem(
      'clubops.demo.session.v1',
      JSON.stringify({ club: 'running-club', role: 'adviser' }),
    ),
  );
  for (const route of ['/inbox', '/settings', '/setup', '/review']) {
    await page.goto(route);
    await expect(page.locator('main h1')).toBeVisible();
    if (route === '/setup') continue; // adviser is redirected to Events
    await expect(
      page.getByRole('button', {
        name: /Read this|Read waiting|Start sample verification|Restore sample|Approve sample deadline/,
      }),
    ).toHaveCount(0);
    const scan = await new AxeBuilder({ page }).include('main').analyze();
    expect(scan.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) }))).toEqual(
      [],
    );
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    if (route === '/inbox')
      await page.screenshot({
        path: `test-results/inbox-${testInfo.project.name}.png`,
        fullPage: true,
      });
  }
});
