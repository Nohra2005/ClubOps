/** Synthetic HTTP responses verify UI boundaries, not actual chatbot teaching quality. */
import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { clubs, createWorkspace } from '../src/api/fixtures';
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

test('F-508: old role preferences and query strings cannot rewrite Ask or Teach', async ({
  page,
}) => {
  const { writes, unexpected } = await fixture(page, 'treasurer');
  await page.addInitScript(() =>
    localStorage.setItem(
      'clubops.role-start.' +
        JSON.stringify([1, 'http', 'running-club', 'm-role-test', 'treasurer']),
      JSON.stringify({ version: 1, step: 2, status: 'active', learning: true }),
    ),
  );
  await page.goto('/chat?role=president&learning=1');
  await expect(page.getByText(/Help me learn my/)).toHaveCount(0);
  await expect(page.getByText('See the context included with my question')).toHaveCount(0);
  await page.getByLabel('Ask your club', { exact: true }).fill('What should I check?');
  await page.getByRole('button', { name: 'Ask ClubOps', exact: true }).click();
  await expect.poll(() => writes.length).toBe(1);
  expect(writes[0]).toEqual({ path: '/api/chat/ask', text: 'What should I check?' });
  await page.getByRole('button', { name: 'Teach the club', exact: true }).click();
  await page.getByLabel('Teach your club', { exact: true }).fill('Synthetic outgoing note.');
  await page.getByRole('button', { name: 'Send fact for review', exact: true }).click();
  await expect.poll(() => writes.length).toBe(2);
  expect(writes[1]).toEqual({ path: '/api/chat/teach', text: 'Synthetic outgoing note.' });
  await page.goto('/events');
  await expect(page.getByRole('region', { name: 'Start your role' })).toHaveCount(0);
  await expect(page.getByRole('complementary', { name: 'Role walkthrough' })).toHaveCount(0);
  expect(unexpected).toEqual([]);
});

test('F-506: real turnover cannot activate through a URL, local draft or preview role', async ({
  page,
}) => {
  const { writes, unexpected } = await fixture(page);
  await page.addInitScript(() =>
    localStorage.setItem(
      'clubops.demo.workspace.v1.running-club',
      JSON.stringify({ turnover: { active: { id: 'forged', label: 'Forged term' } } }),
    ),
  );
  await page.goto('/settings/turnover?activate=1&role=president');
  await expect(page.getByRole('heading', { name: 'Cabinet turnover', exact: true })).toBeVisible();
  await expect(
    page.getByText('Term activation is not available yet. Your current cabinet remains active.'),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /Activate|Confirm activation/ })).toHaveCount(0);
  expect(writes).toEqual([]);
  expect(unexpected).toEqual([]);
  const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(a11y.violations).toEqual([]);
});

test('advisers keep the sourced reference and cannot manage turnover', async ({ page }) => {
  const { writes, unexpected } = await fixture(page, 'adviser');
  await page.goto('/handover');
  await expect(page.getByText('Synthetic approved lesson.', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign off handover', exact: true })).toHaveCount(0);
  await page.goto('/settings/turnover');
  await expect(
    page.getByText('Only the president manages cabinet turnover.', { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /Save and review|Activate/ })).toHaveCount(0);
  expect(writes).toEqual([]);
  expect(unexpected).toEqual([]);
});
