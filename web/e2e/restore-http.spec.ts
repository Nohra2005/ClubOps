/** Candidate #96 contract, synthetic facts; no production memory or provider calls. */
import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { clubs, createWorkspace } from '../src/api/fixtures';
import type { KnowledgeItem } from '../src/api/types';

const workspace = createWorkspace('running-club');
const expired: KnowledgeItem = {
  ...workspace.knowledge.find((item) => item.tab === 'tips')!,
  item_id: 'expired-synthetic',
  title: 'Synthetic expired club fact',
  statement: 'The synthetic club prefers the sample venue.',
  tab: 'tips',
  scope: 'club',
  status: 'may_be_outdated',
  sources: [],
  history: [],
  used_in: [],
};
test.beforeEach(async ({ page }) => {
  await page.route('**/api/me', (route) =>
    route.fulfill({
      json: {
        user: workspace.members[0],
        role: 'president',
        club: clubs[0],
        counts: { overdue_events: 0, review: 0, reminders: 0 },
      },
    }),
  );
});

test('archive separates non-current knowledge and restores only after an explicit date confirmation', async ({
  page,
}) => {
  let restored = false;
  let listCalls = 0;
  const bodies: unknown[] = [];
  await page.route('**/api/knowledge**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/restore')) {
      expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
      bodies.push(route.request().postDataJSON());
      restored = true;
      return route.fulfill({ json: { ...expired, status: 'current' } });
    }
    if (path === '/api/knowledge') {
      listCalls++;
      return route.fulfill({
        json: [
          {
            ...expired,
            item_id: 'current-synthetic',
            title: 'Synthetic current fact',
            status: 'current',
          },
          expired,
          {
            ...expired,
            item_id: 'retired-synthetic',
            title: 'Synthetic retired fact',
            status: 'retired',
          },
        ],
      });
    }
    return route.fulfill({ json: { ...expired, status: restored ? 'current' : expired.status } });
  });
  await page.goto('/knowledge?tab=tips');
  await expect(
    page.getByRole('heading', { name: 'Synthetic current fact', exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: expired.title, exact: true })).toHaveCount(0);
  const before = listCalls;
  await page
    .getByRole('group', { name: 'Knowledge lifetime' })
    .getByRole('button', { name: 'Archive', exact: true })
    .click();
  await expect(page.getByRole('heading', { name: expired.title, exact: true })).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Synthetic retired fact', exact: true }),
  ).toBeVisible();
  expect(listCalls).toBe(before);
  await page.getByRole('link', { name: expired.title, exact: true }).click();
  await page.getByRole('button', { name: 'Restore expired fact', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('button', { name: 'Confirm Restore', exact: true })).toBeDisabled();
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  expect(bodies).toEqual([]);
  await page.getByRole('button', { name: 'Restore expired fact', exact: true }).click();
  await dialog.getByLabel('New end date', { exact: true }).fill('2099-06-30');
  expect(bodies).toEqual([]);
  expect((await new AxeBuilder({ page }).include('dialog[open]').analyze()).violations).toEqual([]);
  await dialog.getByRole('button', { name: 'Confirm Restore', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Restore expired fact', exact: true })).toHaveCount(
    0,
  );
  await expect(page.getByRole('heading', { name: expired.title, exact: true })).toBeVisible();
  expect(bodies).toEqual([{ valid_to: '2099-06-30' }]);
});

test('Restore can explicitly remove the end date without making a model or approval request', async ({
  page,
}) => {
  const writes: string[] = [];
  const bodies: unknown[] = [];
  let restored = false;
  page.on('request', (request) => {
    if (request.method() !== 'GET') writes.push(new URL(request.url()).pathname);
  });
  await page.route('**/api/knowledge/**', (route) => {
    if (route.request().method() === 'POST') {
      bodies.push(route.request().postDataJSON());
      restored = true;
    }
    return route.fulfill({ json: { ...expired, status: restored ? 'current' : expired.status } });
  });
  await page.goto(`/knowledge/${expired.item_id}`);
  await page.getByRole('button', { name: 'Restore expired fact', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('No end date', { exact: true }).check();
  await dialog.getByRole('button', { name: 'Confirm Restore', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Restore expired fact', exact: true })).toHaveCount(
    0,
  );
  expect(bodies).toEqual([{ valid_to: null }]);
  expect(writes).toEqual([`/api/knowledge/${expired.item_id}/restore`]);
});

for (const [name, role, scope, status] of [
  ['AUB-wide', 'president', 'aub', 'may_be_outdated'],
  ['retired', 'president', 'club', 'retired'],
  ['cabinet non-president', 'secretary', 'club', 'may_be_outdated'],
  ['adviser', 'adviser', 'club', 'may_be_outdated'],
] as const) {
  test(`Restore stays hidden for ${name}`, async ({ page }) => {
    let posts = 0;
    await page.route('**/api/me', (route) =>
      route.fulfill({
        json: {
          user: { ...workspace.members[0], role },
          role,
          club: clubs[0],
          counts: { overdue_events: 0, review: 0, reminders: 0 },
        },
      }),
    );
    await page.route('**/api/knowledge/**', (route) => {
      if (route.request().method() === 'POST') posts++;
      return route.fulfill({ json: { ...expired, scope, status } });
    });
    await page.goto(`/knowledge/${expired.item_id}`);
    await expect(page.getByRole('heading', { name: expired.title, exact: true })).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Restore expired fact', exact: true }),
    ).toHaveCount(0);
    expect(posts).toBe(0);
  });
}

test('disputed Restore shows the plain 409 explanation, preserves the date and sends no retry', async ({
  page,
}) => {
  let posts = 0;
  const detail = 'Synthetic disputed <b>fact</b>: review it first.';
  await page.route('**/api/knowledge/**', (route) => {
    if (route.request().method() === 'POST') {
      posts++;
      return route.fulfill({ status: 409, json: { detail } });
    }
    return route.fulfill({ json: expired });
  });
  await page.goto(`/knowledge/${expired.item_id}`);
  await page.getByRole('button', { name: 'Restore expired fact', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('New end date', { exact: true }).fill('2099-06-30');
  await dialog.getByRole('button', { name: 'Confirm Restore', exact: true }).click();
  await expect(dialog.getByRole('alert')).toHaveText(detail);
  await expect(dialog.getByLabel('New end date', { exact: true })).toHaveValue('2099-06-30');
  await expect(dialog.locator('b')).toHaveCount(0);
  expect(posts).toBe(1);
});

test('unconfirmed Restore requires a fresh fact read and never trusts a different item acknowledgement', async ({
  page,
}) => {
  let posts = 0;
  let restored = false;
  await page.route('**/api/knowledge/**', (route) => {
    if (route.request().method() === 'POST') {
      posts++;
      restored = true;
      return route.fulfill({
        json: {
          ...expired,
          item_id: 'wrong-item',
          status: 'current',
          private: 'PRIVATE_ACK_CANARY',
        },
      });
    }
    return route.fulfill({ json: { ...expired, status: restored ? 'current' : expired.status } });
  });
  await page.goto(`/knowledge/${expired.item_id}`);
  await page.getByRole('button', { name: 'Restore expired fact', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('No end date', { exact: true }).check();
  await dialog.getByRole('button', { name: 'Confirm Restore', exact: true }).click();
  await expect(dialog.getByRole('alert')).toContainText('not confirmed');
  await expect(dialog.getByRole('button', { name: 'Confirm Restore', exact: true })).toBeDisabled();
  await expect(dialog).not.toContainText('PRIVATE_ACK_CANARY');
  await dialog.getByRole('button', { name: 'Reload fact', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Restore expired fact', exact: true })).toHaveCount(
    0,
  );
  await expect(page.getByRole('heading', { name: expired.title, exact: true })).toBeVisible();
  expect(posts).toBe(1);
});
