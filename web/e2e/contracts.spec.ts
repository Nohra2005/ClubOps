/** These tests use the real HTTP adapter with intercepted synthetic responses, not a deployed API. */
import { expect, test } from '@playwright/test';
import { clubs, createWorkspace } from '../src/api/fixtures';
import { todayInBeirut } from '../src/lib';

test.beforeEach(async ({ page }) => {
  const workspace = createWorkspace('running-club');
  await page.route('**/api/me', (route) =>
    route.fulfill({
      json: {
        user: workspace.members.find((member) => member.role === 'president'),
        role: 'president',
        club: clubs[0],
        counts: { overdue_events: 0, review: 0, reminders: 0 },
      },
    }),
  );
});

test('HTTP planner polls running, shows the published question and handles at_limit', async ({
  page,
}) => {
  let polls = 0;
  let answered = false;
  const wireRun = {
    run_id: 'run-wire-example',
    club_id: 'running-club',
    event_id: null,
    steps_used: 1,
    step_limit: 8,
    cost_usd: '0.006',
    cost_limit_usd: '0.025',
  };
  await page.route('**/api/runs/run-wire-example', (route) => {
    polls++;
    const question = !answered && polls > 1;
    return route.fulfill({
      json: {
        ...wireRun,
        status: answered ? 'at_limit' : question ? 'waiting_for_user' : 'running',
        steps: [
          {
            n: 1,
            tool: question ? 'ask-user' : 'search-memory',
            text: question ? 'Will there be prizes?' : 'Read the approved notes',
            state: question ? 'question' : 'done',
          },
        ],
      },
    });
  });
  await page.route('**/api/runs/run-wire-example/answer', async (route) => {
    expect(route.request().postDataJSON()).toEqual({ text: 'No prizes' });
    answered = true;
    await route.fulfill({
      json: {
        ...wireRun,
        status: 'at_limit',
        steps: [{ n: 1, tool: 'search-memory', text: 'Read the approved notes', state: 'done' }],
      },
    });
  });
  await page.goto('/events/new?run=run-wire-example');
  await expect(page.getByPlaceholder('Your answer')).toBeVisible();
  await expect(page.locator('.agent-panel')).toContainText('Will there be prizes?');
  await expect(page.locator('.agent-panel')).toContainText('$0.025');
  await page.getByPlaceholder('Your answer').fill('No prizes');
  await page.getByRole('button', { name: 'Answer and continue' }).click();
  await expect(page.getByText('This run reached its limit.', { exact: true })).toBeVisible();
  expect(polls).toBeGreaterThanOrEqual(2);
  await expect(page.getByRole('button', { name: 'Approve plan', exact: true })).toHaveCount(0);
});

test('HTTP chat handles nullable uncertainty, citation IDs and HTTP-200 failures', async ({
  page,
}) => {
  let calls = 0;
  await page.route('**/api/chat/ask', (route) => {
    calls++;
    const json =
      calls === 1
        ? {
            status: 'ok',
            degraded: true,
            data: {
              known: false,
              text: 'Ask the example office about this specific case.',
              basis: 'none',
              citations: [],
              ask: { who: 'Example office', role: null },
              look_in: null,
            },
          }
        : calls === 2
          ? {
              known: true,
              text: 'These synthetic sources disagree.',
              basis: 'disputed',
              citations: ['kh-wire-example'],
            }
          : {
              status: 'failed',
              error: { code: 'upstream_error', message: 'PRIVATE UPSTREAM DIAGNOSTIC' },
              data: null,
            };
    return route.fulfill({ json });
  });
  await page.goto('/chat');
  await page.getByLabel('Ask your club', { exact: true }).fill('A synthetic first question');
  await page.getByRole('button', { name: 'Ask ClubOps' }).click();
  await expect(
    page.getByText('Ask the example office about this specific case.', { exact: true }),
  ).toBeVisible();
  await expect(page.locator('.not-sure')).toContainText('Example office');
  await expect(page.locator('.not-sure')).not.toContainText('Look in');
  await expect(page.getByText(/Simple version: some checks were skipped/)).toBeVisible();
  await page.getByLabel('Ask your club', { exact: true }).fill('A synthetic second question');
  await page.getByRole('button', { name: 'Ask ClubOps' }).click();
  await expect(page.getByRole('link', { name: 'Review the disagreement' })).toHaveAttribute(
    'href',
    '/review',
  );
  await expect(page.locator('.source-chip')).toHaveAttribute('href', '/knowledge/kh-wire-example');
  await page.getByLabel('Ask your club', { exact: true }).fill('Keep this failed question');
  await page.getByRole('button', { name: 'Ask ClubOps' }).click();
  await expect(page.getByRole('alert')).toContainText("ClubOps couldn't finish this.");
  await expect(page.getByLabel('Ask your club', { exact: true })).toHaveValue(
    'Keep this failed question',
  );
  await expect(page.getByText('PRIVATE UPSTREAM DIAGNOSTIC')).toHaveCount(0);
});

test('HTTP calendar omits cancelled items and handles nullable times and member ownership', async ({
  page,
}) => {
  const open = {
    item_id: 'club/wire-example',
    club_id: 'running-club',
    event_id: null,
    kind: 'task',
    title: 'Synthetic open reminder',
    date: `${todayInBeirut().slice(0, 7)}-15`,
    start: null,
    end: null,
    owner_role: 'member',
    status: 'open',
    reminders: [{ before_days: null, on_day_at: '08:00:00', after_days: null }],
    repeat_until_done: false,
    link: null,
  };
  await page.route('**/api/calendar?*', (route) =>
    route.fulfill({
      json: {
        connected: false,
        items: [
          open,
          {
            ...open,
            item_id: 'club/cancelled-example',
            title: 'Synthetic cancelled reminder',
            status: 'cancelled',
          },
        ],
      },
    }),
  );
  await page.goto('/calendar');
  await expect(page.getByRole('button', { name: /^Synthetic open reminder/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /^Synthetic cancelled reminder/ })).toHaveCount(0);
  await page.getByRole('button', { name: /^Synthetic open reminder/ }).click();
  await expect(page.getByRole('dialog')).toContainText('Member');
  await expect(page.getByRole('dialog')).toContainText('A club-wide reminder.');
});

test('HTTP draft rejects a sent result and then accepts a matching published draft', async ({
  page,
}) => {
  const workspace = createWorkspace('running-club');
  const event = workspace.events.find((item) => item.event_id === 'ev-sunset-run')!;
  event.drafts = {};
  event.agent_run = undefined;
  let calls = 0;
  await page.route('**/api/cabinet', (route) => route.fulfill({ json: workspace.members }));
  await page.route('**/api/events/ev-sunset-run', (route) => route.fulfill({ json: event }));
  await page.route('**/api/events/ev-sunset-run/drafts/announcement', (route) => {
    calls++;
    const body = 'A synthetic announcement for human review.';
    if (calls > 1) event.drafts.announcement = { type: 'announcement', text: body, state: 'draft' };
    return route.fulfill({
      json: {
        event_id: event.event_id,
        draft_type: 'whatsapp_announcement',
        template_version: 'synthetic-1',
        body,
        based_on: [],
        subject: null,
        state: calls === 1 ? 'sent' : 'draft',
      },
    });
  });
  await page.goto('/events/ev-sunset-run?tab=drafts');
  const card = page
    .locator('.draft-card')
    .filter({ has: page.getByRole('heading', { name: 'WhatsApp announcement', exact: true }) });
  await card.getByRole('button', { name: 'Write draft', exact: true }).click();
  await expect(card.getByRole('alert')).toContainText('incompatible data');
  await expect(card.getByRole('textbox')).toHaveCount(0);
  await card.getByRole('button', { name: 'Write draft', exact: true }).click();
  await expect(card.getByRole('textbox')).toHaveValue('A synthetic announcement for human review.');
  await expect(card).toContainText('Draft · not sent');
});
