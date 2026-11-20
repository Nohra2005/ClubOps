/** Candidate #95 contract, synthetic intercepted responses; no real mail/model calls. */
import { expect, test, type Page } from '@playwright/test';
import { clubs, createWorkspace } from '../src/api/fixtures';

const message = {
  id: 'msg-synthetic',
  subject: 'Synthetic OSA forward',
  date: '',
  forwarded_by: '',
};
test.beforeEach(async ({ page }) => {
  await page.route('**/api/me', (route) =>
    route.fulfill({
      json: {
        user: createWorkspace('running-club').members[0],
        role: 'president',
        club: clubs[0],
        counts: { overdue_events: 0, review: 0, reminders: 0 },
      },
    }),
  );
});
function writes(page: Page) {
  const calls: string[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/') && request.method() !== 'GET')
      calls.push(new URL(request.url()).pathname);
  });
  return calls;
}

test('paid inbox read needs confirmation, Cancel does nothing and rapid clicks produce one request', async ({
  page,
}) => {
  const calls = writes(page);
  let release: () => void = () => {};
  await page.route('**/api/inbox**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/capture')) {
      expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
      expect(route.request().postData()).toBeNull();
      await new Promise<void>((resolve) => {
        release = resolve;
      });
      return route.fulfill({ json: { proposals: ['p-1', 'p-1', 'p-2'], skipped: [] } });
    }
    // Deliberately stale metadata must not offer another read after acknowledgement.
    return route.fulfill({ json: path.endsWith('/skipped') ? [] : [message] });
  });
  await page.goto('/inbox');
  const read = page.getByRole('button', { name: 'Read this · costs money', exact: true });
  await read.click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('paid AI read');
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  expect(calls).toEqual([]);
  await read.click();
  await dialog
    .getByRole('button', { name: 'Confirm paid read', exact: true })
    .evaluate((button: HTMLButtonElement) => {
      button.click();
      button.click();
    });
  await expect.poll(() => calls.length).toBe(1);
  await expect(dialog.getByRole('button', { name: 'Reading…', exact: true })).toBeDisabled();
  release();
  await expect(
    page.getByText('Read result received. 2 Review card(s) proposed; none approved.', {
      exact: true,
    }),
  ).toBeVisible();
  await expect(read).toHaveCount(0);
  await expect(page.getByText(/Read result already received/)).toBeVisible();
  expect(calls).toEqual(['/api/inbox/msg-synthetic/capture']);
  expect(
    await page.evaluate(() =>
      JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)]),
    ),
  ).not.toContain(message.subject);
});

for (const [name, skipped] of [
  ['no fact', []],
  ['unusable material', ['<b>Synthetic unusable fragment</b>']],
] as const) {
  test(`paid inbox acknowledgement with ${name} is complete and never auto-retried`, async ({
    page,
  }) => {
    const calls = writes(page);
    let done = false;
    await page.route('**/api/inbox**', (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith('/capture')) {
        done = true;
        return route.fulfill({ json: { proposals: [], skipped } });
      }
      return route.fulfill({ json: path.endsWith('/skipped') || done ? [] : [message] });
    });
    await page.goto('/inbox');
    await page.getByRole('button', { name: 'Read this · costs money', exact: true }).click();
    await page
      .getByRole('dialog')
      .getByRole('button', { name: 'Confirm paid read', exact: true })
      .click();
    await expect(
      page.getByText('Read result received. No facts were proposed; no fact was approved.', {
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.getByText('No waiting email.', { exact: true })).toBeVisible();
    if (skipped.length) {
      await expect(page.getByText(skipped[0], { exact: true })).toBeVisible();
      await expect(page.locator('main b')).toHaveCount(0);
    }
    expect(calls).toEqual(['/api/inbox/msg-synthetic/capture']);
  });
}

test('unconfirmed paid result requires a successful fresh list and another explicit confirmation', async ({
  page,
}) => {
  const calls = writes(page);
  let done = false;
  let failRefresh = false;
  await page.route('**/api/inbox**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/capture')) {
      if (calls.length === 1)
        return route.fulfill({ json: { proposals: 'malformed', skipped: [] } });
      done = true;
      return route.fulfill({ json: { proposals: [], skipped: [] } });
    }
    if (path.endsWith('/skipped')) return route.fulfill({ json: [] });
    return failRefresh
      ? route.fulfill({ status: 503, json: { detail: 'Synthetic temporary failure' } })
      : route.fulfill({ json: done ? [] : [message] });
  });
  await page.goto('/inbox');
  await page.getByRole('button', { name: 'Read this · costs money', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Confirm paid read', exact: true }).click();
  await expect(dialog.getByRole('alert')).toContainText('not confirmed');
  await expect(
    dialog.getByRole('button', { name: 'Confirm paid read', exact: true }),
  ).toBeDisabled();
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Refresh before retrying', exact: true }),
  ).toBeDisabled();
  failRefresh = true;
  await page.getByRole('button', { name: 'Refresh waiting email', exact: true }).click();
  const waiting = page.getByRole('region', { name: 'Waiting email', exact: true });
  await expect(waiting.getByRole('alert')).toBeVisible();
  expect(calls).toHaveLength(1);
  failRefresh = false;
  await waiting.getByRole('button', { name: 'Try again', exact: true }).click();
  await page.getByRole('button', { name: 'Read this · costs money', exact: true }).click();
  expect(calls).toHaveLength(1);
  await page
    .getByRole('dialog')
    .getByRole('button', { name: 'Confirm paid read', exact: true })
    .click();
  await expect(page.getByText('No waiting email.', { exact: true })).toBeVisible();
  expect(calls).toEqual(['/api/inbox/msg-synthetic/capture', '/api/inbox/msg-synthetic/capture']);
});

for (const status of [409, 502]) {
  test(`paid inbox ${status} stays unconfirmed without an automatic retry`, async ({ page }) => {
    const calls = writes(page);
    await page.route('**/api/inbox**', (route) => {
      const path = new URL(route.request().url()).pathname;
      return path.endsWith('/capture')
        ? route.fulfill({ status, json: { detail: 'PRIVATE_DIAGNOSTIC_CANARY' } })
        : route.fulfill({ json: path.endsWith('/skipped') ? [] : [message] });
    });
    await page.goto('/inbox');
    await page.getByRole('button', { name: 'Read this · costs money', exact: true }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Confirm paid read', exact: true }).click();
    await expect(dialog.getByRole('alert')).toBeVisible();
    await expect(
      dialog.getByRole('button', { name: 'Confirm paid read', exact: true }),
    ).toBeDisabled();
    await expect(dialog).not.toContainText('PRIVATE_DIAGNOSTIC_CANARY');
    expect(calls).toEqual(['/api/inbox/msg-synthetic/capture']);
  });
}
