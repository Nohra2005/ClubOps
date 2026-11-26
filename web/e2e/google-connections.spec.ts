/** Synthetic HTTP tests: no real Google requests, consent or mail. */
import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { clubs, createWorkspace } from '../src/api/fixtures';

async function fixture(page: Page, role = 'president', manager = true) {
  const workspace = createWorkspace('running-club');
  const current = {
    state: 'not_connected',
    source: null as string | null,
    can_connect: true,
    can_manage: manager,
    access_changes_waiting: 2,
  };
  const writes: { path: string; method: string }[] = [];
  let fetchDenied = false;
  let badUrl = false;
  await page.route('**/api/**', (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) return route.fallback();
    if (request.method() !== 'GET') {
      expect(request.headers()['x-requested-with']).toBe('ClubOps');
      writes.push({ path, method: request.method() });
    }
    if (path === '/api/me')
      return route.fulfill({
        json: {
          user: { ...workspace.members[0], role },
          role,
          club: clubs[0],
          counts: { overdue_events: 0, review: 0, reminders: 0 },
        },
      });
    if (path === '/api/calendar/connection' || path === '/api/inbox/gmail')
      return route.fulfill({ json: current });
    if (path.endsWith('/connect')) {
      if (request.method() === 'DELETE') {
        current.state = 'not_connected';
        return route.fulfill({ status: 204 });
      }
      return route.fulfill({
        json: {
          url: badUrl
            ? 'javascript:alert(1)'
            : 'https://accounts.google.com/o/oauth2/v2/auth?state=synthetic',
        },
      });
    }
    if (path === '/api/inbox/fetch')
      return fetchDenied
        ? route.fulfill({
            status: 409,
            json: { detail: 'Synthetic key expired. Reconnect Gmail.' },
          })
        : route.fulfill({
            json: {
              queued: 2,
              skipped: 1,
              not_for_a_club: 3,
              refreshed: true,
              mail: 'PRIVATE_MAIL_CANARY',
            },
          });
    if (path === '/api/calendar') return route.fulfill({ json: { items: [], connected: false } });
    return route.fulfill({ json: [] });
  });
  await page.route('https://accounts.google.com/**', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<h1>Synthetic Google authorization</h1>' }),
  );
  return {
    current,
    writes,
    denyFetch: () => {
      fetchDenied = true;
    },
    badAuthorization: () => {
      badUrl = true;
    },
  };
}

test('Calendar exposes all states, validates callback against status and does not write on opening', async ({
  page,
}) => {
  const f = await fixture(page);
  for (const state of ['not_set_up', 'not_connected', 'connected', 'reconnect']) {
    f.current.state = state;
    f.current.can_connect = state !== 'not_set_up';
    await page.goto('/calendar?google=connected');
    const panel = page.getByRole('region', { name: 'Google Calendar connection' });
    await expect(panel.getByRole('button', { name: 'Refresh status', exact: true })).toBeEnabled();
    await expect(panel).toContainText('2 cabinet access change(s) waiting.');
    await expect(
      panel.getByRole('button', {
        name: state === 'reconnect' ? 'Reconnect Google Calendar' : 'Connect Google Calendar',
        exact: true,
      }),
    ).toHaveCount(['not_connected', 'reconnect'].includes(state) ? 1 : 0);
    if (state !== 'connected')
      await expect(panel).toContainText('connection has not been confirmed');
  }
  expect(f.writes).toEqual([]);
});

test('Gmail fetch displays counts, refreshes lists and exposes the scoped plain 409', async ({
  page,
}) => {
  const f = await fixture(page, 'events', false);
  f.current.state = 'connected';
  f.current.source = 'host';
  await page.goto('/inbox?gmail=denied');
  const panel = page.getByRole('region', { name: 'Gmail inbox connection' });
  await expect(panel).toContainText('Google connection cancelled');
  await expect(panel.getByRole('button', { name: /Disconnect|Connect/ })).toHaveCount(0);
  await panel.getByRole('button', { name: 'Fetch email', exact: true }).click();
  await expect(panel).toContainText('Fetched: 2 queued, 1 skipped, 3 without a club.');
  await expect(page.getByRole('main')).not.toContainText('PRIVATE_MAIL_CANARY');
  await expect(panel.getByRole('button', { name: 'Fetch email', exact: true })).toBeEnabled();
  f.denyFetch();
  await panel.getByRole('button', { name: 'Fetch email', exact: true }).click();
  await expect(panel.getByRole('alert')).toContainText('Synthetic key expired. Reconnect Gmail.');
  expect(f.writes.map((row) => row.path)).toEqual(['/api/inbox/fetch', '/api/inbox/fetch']);
});

test('Connect opens Google only after a click; disconnect needs confirmation', async ({ page }) => {
  const f = await fixture(page);
  await page.goto('/inbox');
  await page.getByRole('button', { name: 'Connect Gmail inbox', exact: true }).click();
  await expect(page).toHaveURL(/https:\/\/accounts.google.com\/o\/oauth2\/v2\/auth/);
  expect(f.writes).toEqual([{ path: '/api/inbox/gmail/connect', method: 'POST' }]);
  f.current.state = 'connected';
  f.current.source = 'app';
  await page.goto('/inbox?gmail=connected');
  await page.getByRole('button', { name: 'Disconnect Gmail inbox', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
  expect(f.writes).toHaveLength(1);
  await page.getByRole('button', { name: 'Disconnect Gmail inbox', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm disconnect', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Connect Gmail inbox', exact: true }),
  ).toBeVisible();
  expect(f.writes[1]).toEqual({ path: '/api/inbox/gmail/connect', method: 'DELETE' });
  await page.goto('/calendar');
  await page.getByRole('button', { name: 'Connect Google Calendar', exact: true }).click();
  await expect(page).toHaveURL(/accounts.google.com/);
  expect(f.writes[2]).toEqual({ path: '/api/calendar/connect', method: 'POST' });
});

test('advisers have no connection/fetch controls and unsafe authorization never navigates', async ({
  page,
}) => {
  const f = await fixture(page, 'adviser', true);
  await page.goto('/calendar');
  await expect(page.getByRole('region', { name: 'Google Calendar connection' })).toHaveCount(0);
  await page.goto('/inbox');
  await expect(
    page.getByRole('heading', { name: 'Inbox is for cabinet members.', exact: true }),
  ).toBeVisible();
  expect(f.writes).toEqual([]);
});

test('unsafe authorization stays on the page and connection controls fit phone/Axe', async ({
  page,
}) => {
  const f = await fixture(page);
  f.badAuthorization();
  await page.goto('/inbox?gmail=failed');
  await page.getByRole('button', { name: 'Connect Gmail inbox', exact: true }).click();
  await expect(page).toHaveURL(/\/inbox\?gmail=failed$/);
  await expect(page.getByRole('region', { name: 'Gmail inbox connection' })).toContainText(
    'address could not be confirmed',
  );
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
