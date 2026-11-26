/** Synthetic HTTP responses verify UI boundaries, not actual chatbot teaching quality. */
import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { clubs, createWorkspace } from '../src/api/fixtures';
import { progressKey } from '../src/handover/progress';
import type { Role } from '../src/api/types';

async function fixture(page: Page, role: Role = 'president', member = 'm-role-test') {
  const writes: { path: string; text: string }[] = [];
  const unexpected: string[] = [];
  const workspace = createWorkspace('running-club');
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) return route.fallback();
    if (path === '/api/me')
      return route.fulfill({
        json: {
          user: { ...workspace.members[0], member_id: member, role },
          role,
          club: clubs[0],
          counts: { overdue_events: 0, review: 0, reminders: 0 },
        },
      });
    if (request.method() !== 'GET') {
      writes.push({ path, text: request.postDataJSON()?.text ?? '' });
      if (path === '/api/chat/ask')
        return route.fulfill({
          json: {
            kind: 'unknown',
            known: false,
            basis: 'none',
            citations: [],
            text: 'No approved answer in this synthetic club.',
            ask: { who: 'Outgoing officer' },
            look_in: 'Club sources',
          },
        });
      if (path === '/api/chat/teach')
        return route.fulfill({
          json: {
            kind: 'learned',
            text: 'Synthetic note queued for review.',
            review_id: 'rv-synthetic',
          },
        });
      unexpected.push(path);
      return route.fulfill({ status: 501, json: { detail: 'Unpublished' } });
    }
    if (path === '/api/calendar/connection' || path === '/api/inbox/gmail')
      return route.fulfill({
        json: {
          state: 'not_set_up',
          source: null,
          can_connect: false,
          can_manage: false,
          access_changes_waiting: 0,
        },
      });
    if (path === '/api/calendar') return route.fulfill({ json: { items: [], connected: false } });
    if (path.startsWith('/api/handover/'))
      return route.fulfill({
        json: {
          role: path.split('/').at(-1),
          sections: [
            {
              title: 'Lessons',
              entries: [
                {
                  text: 'Synthetic approved lesson.',
                  source: {
                    item_id: 'kh-synthetic',
                    label: 'Synthetic source',
                    quote: 'Synthetic source excerpt.',
                  },
                },
              ],
            },
          ],
          gaps: [
            {
              topic: 'Missing venue contact',
              question: 'Who should the next officer contact?',
              ask: 'Outgoing officer',
              look_in: 'Source documents',
            },
          ],
        },
      });
    if (['/api/events', '/api/knowledge', '/api/review'].includes(path))
      return route.fulfill({ json: [] });
    unexpected.push(path);
    return route.fulfill({ status: 501, json: { detail: 'Unpublished' } });
  });
  return { writes, unexpected };
}

test('walkthrough highlights real destinations, pauses, resumes and finishes without writes', async ({
  page,
}, testInfo) => {
  const { writes, unexpected } = await fixture(page);
  await page.goto('/events');
  await expect(page.getByRole('region', { name: 'Start your role' })).toBeVisible();
  await expect(
    page
      .getByRole('navigation', { name: 'Main navigation' })
      .getByText('Handover', { exact: true }),
  ).toHaveCount(0);
  await page.getByRole('link', { name: 'Start here' }).click();
  await page.screenshot({
    path: `../../c37-visual/start-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole('button', { name: 'Start walkthrough' }).click();
  const tour = page.getByRole('complementary', { name: 'Role walkthrough' });
  await expect(tour).toContainText('1 OF 4');
  await page.screenshot({
    path: `../../c37-visual/tour-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await expect(page.locator('.role-tour-highlight:visible').first()).toBeVisible();
  await tour.getByRole('button', { name: 'Next step' }).click();
  await expect(page).toHaveURL(/\/calendar$/);
  await tour.getByRole('button', { name: 'Pause', exact: true }).click();
  await page.reload();
  await expect(tour).toHaveCount(0);
  await page.goto('/handover');
  await page.getByRole('button', { name: 'Resume walkthrough' }).click();
  await expect(tour).toContainText('2 OF 4');
  await tour.getByRole('button', { name: 'Skip this step' }).click();
  await expect(page).toHaveURL(/\/knowledge$/);
  await tour.getByRole('button', { name: 'Next step' }).click();
  await expect(page).toHaveURL(/\/chat$/);
  await tour.getByRole('button', { name: 'Finish introduction' }).click();
  await expect(page.getByRole('button', { name: 'Replay walkthrough' })).toBeVisible();
  expect(writes).toEqual([]);
  expect(unexpected).toEqual([]);
  await expect(page.locator('body')).toHaveJSProperty(
    'scrollWidth',
    await page.locator('body').evaluate((el) => el.clientWidth),
  );
  const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(a11y.violations).toEqual([]);
});

test('role context is explicit, survives reload and never contaminates Teach', async ({ page }) => {
  const { writes, unexpected } = await fixture(page, 'treasurer');
  await page.goto('/chat?role=president&learning=1');
  const checkbox = page.getByRole('checkbox', { name: /Help me learn/ });
  await expect(checkbox).not.toBeChecked(); // a URL cannot opt somebody in
  await checkbox.check();
  await page.reload();
  await expect(checkbox).toBeChecked();
  await page.getByLabel('Ask your club', { exact: true }).fill('What should I check?');
  expect(writes).toEqual([]);
  await page
    .locator('.chat-compose form')
    .evaluate((form) => (form as HTMLFormElement).requestSubmit());
  await expect.poll(() => writes.length).toBe(1);
  expect(writes[0].text).toContain('Treasurer');
  expect(writes[0].text).not.toContain('President');
  await page.getByRole('button', { name: 'Teach the club', exact: true }).click();
  await page.getByLabel('Teach your club', { exact: true }).fill('Synthetic outgoing note.');
  await page
    .locator('.chat-compose form')
    .evaluate((form) => (form as HTMLFormElement).requestSubmit());
  await expect.poll(() => writes.length).toBe(2);
  expect(writes[1]).toEqual({ path: '/api/chat/teach', text: 'Synthetic outgoing note.' });
  expect(unexpected).toEqual([]);
});

test('another account or role cannot inherit paused progress and advisers have no write tour', async ({
  page,
}) => {
  await fixture(page, 'adviser', 'm-other');
  await page.addInitScript(
    ({ key }) =>
      localStorage.setItem(
        key,
        JSON.stringify({ version: 1, step: 2, status: 'paused', learning: true }),
      ),
    { key: progressKey('http', 'running-club', 'm-role-test', 'president') },
  );
  await page.goto('/handover');
  await expect(
    page.getByRole('button', { name: /Start walkthrough|Resume walkthrough/ }),
  ).toHaveCount(0);
  await page.getByText('Reference guide, sources and outgoing questions', { exact: true }).click();
  await expect(page.getByText('Synthetic approved lesson.', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign off handover', exact: true })).toHaveCount(0);
  await page.goto('/chat?learning=1');
  await expect(page.getByRole('checkbox', { name: /Help me learn/ })).toHaveCount(0);
});

test('storage failure keeps the tour usable and a different member starts fresh', async ({
  page,
}) => {
  const { writes } = await fixture(page, 'events', 'm-new-officer');
  await page.addInitScript(
    ({ key }) => {
      localStorage.setItem(
        key,
        JSON.stringify({ version: 1, step: 2, status: 'paused', learning: true }),
      );
      Storage.prototype.setItem = () => {
        throw new DOMException('Synthetic storage unavailable');
      };
    },
    { key: progressKey('http', 'running-club', 'm-role-test', 'events') },
  );
  await page.goto('/handover');
  await expect(page.getByRole('button', { name: 'Start walkthrough' })).toBeVisible();
  await page.getByRole('button', { name: 'Start walkthrough' }).click();
  const tour = page.getByRole('complementary', { name: 'Role walkthrough' });
  await expect(tour).toContainText('1 OF 4');
  await expect(page.locator('.toast[role="status"]')).toContainText(
    'Changes stay in this tab only',
  );
  await tour.getByRole('button', { name: 'Next step' }).click();
  await expect(tour).toContainText('2 OF 4');
  expect(writes).toEqual([]);
});
