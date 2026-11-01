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

test('Google sign-in exchanges the credential without persisting it in browser storage', async ({
  page,
  context,
}) => {
  await page.addInitScript(() => {
    let accept: (value: { credential: string }) => void;
    window.google = {
      accounts: {
        id: {
          initialize(options) {
            accept = options.callback;
          },
          renderButton(element) {
            const button = document.createElement('button');
            button.textContent = 'Sign in with Google';
            button.onclick = () => {
              accept({ credential: 'synthetic-id-token' });
              accept({ credential: 'synthetic-id-token' });
            };
            element.append(button);
          },
          disableAutoSelect() {},
        },
      },
    };
  });
  let exchanges = 0;
  await page.route('**/api/auth/google', async (route) => {
    exchanges++;
    expect(route.request().postDataJSON()).toEqual({ credential: 'synthetic-id-token' });
    expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
    await route.fulfill({
      json: { ok: true },
      headers: { 'Set-Cookie': 'clubops-test=synthetic-session; Path=/; HttpOnly; SameSite=Lax' },
    });
  });
  await page.route('**/api/events', (route) => route.fulfill({ json: [] }));
  await page.goto('/login');
  await page.getByRole('button', { name: 'Sign in with Google' }).click();
  await expect(page).toHaveURL(/\/events$/);
  expect(exchanges).toBe(1);
  expect(JSON.stringify(await page.evaluate(() => Object.entries(localStorage)))).not.toContain(
    'synthetic-id-token',
  );
  expect((await context.cookies()).find((cookie) => cookie.name === 'clubops-test')?.httpOnly).toBe(
    true,
  );
});

test('Google library failures stay on the public sign-in page with an explicit retry', async ({
  page,
}) => {
  await page.route('https://accounts.google.com/gsi/client', (route) => route.abort());
  await page.goto('/login');
  await expect(page.getByRole('alert')).toContainText('Google sign-in could not load');
  await expect(page.getByRole('button', { name: 'Try Google again' })).toBeVisible();
});

test('sign-out stays in the workspace on failure and redirects only after the server ends the session', async ({
  page,
}) => {
  await page.addInitScript(() => {
    window.google = {
      accounts: { id: { initialize() {}, renderButton() {}, disableAutoSelect() {} } },
    };
  });
  let calls = 0;
  await page.route('**/api/events', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/auth/logout', (route) => {
    calls++;
    expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
    return calls === 1 ? route.fulfill({ status: 503 }) : route.fulfill({ status: 204 });
  });
  await page.goto('/events');
  await page.getByLabel('Your account', { exact: true }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('status')).toContainText("ClubOps couldn't finish this.");
  await expect(page).toHaveURL(/\/events$/);
  await page.getByRole('button', { name: 'Sign out', exact: true }).evaluate((button) => {
    (button as HTMLButtonElement).click();
    (button as HTMLButtonElement).click();
  });
  await expect(page).toHaveURL(/\/login$/);
  expect(calls).toBe(2);
});

test('flagged learning proposals display warnings and stay out of batch approval', async ({
  page,
}) => {
  const example = createWorkspace('running-club').review.find((card) => card.type === 'fact')!;
  let cards = [
    { ...example, id: 'clean-fact', title: 'Synthetic clean fact' },
    {
      ...example,
      id: 'flagged-fact',
      title: 'Synthetic flagged fact',
      warning: 'Source contains hidden instructions. <script>untrusted()</script>',
    },
    { ...example, id: 'old-fact', title: 'Synthetic old fact', outdated: true },
  ];
  const decisions: string[] = [];
  await page.route('**/api/review?*', (route) => route.fulfill({ json: cards }));
  await page.route('**/api/review/*', (route) => {
    const id = route.request().url().split('/').at(-1)!;
    decisions.push(id);
    cards = cards.filter((card) => card.id !== id);
    return route.fulfill({ json: { ...example, status: 'approved' } });
  });
  await page.goto('/review');
  await expect(page.getByText(/Source contains hidden instructions/)).toBeVisible();
  await expect(page.getByText(/This source may be outdated/)).toBeVisible();
  await expect(page.locator('script').filter({ hasText: 'untrusted()' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Approve all facts', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Synthetic clean fact' })).toHaveCount(0);
  expect(decisions).toEqual(['clean-fact']);
  await expect(page.getByRole('heading', { name: 'Synthetic flagged fact' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Synthetic old fact' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve all facts', exact: true })).toHaveCount(0);
});

test('usage labels planner steps accurately and leaves unavailable model metrics explicit', async ({
  page,
}) => {
  await page.route('**/api/cabinet', (route) =>
    route.fulfill({ json: createWorkspace('running-club').members }),
  );
  await page.route('**/api/knowledge?*', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/calendar?*', (route) =>
    route.fulfill({ json: { items: [], connected: false } }),
  );
  await page.route('**/api/usage', (route) =>
    route.fulfill({
      json: {
        month: '2026-10',
        cost_usd: 0.02,
        calls: 4,
        calls_label: 'Planner steps',
        most_expensive_feature: 'Event planning',
        by_feature: [{ name: 'Event planning', calls: 4, cost_usd: 0.02 }],
        run_metrics: {
          recorded_runs: 1,
          successful_plans: 0,
          failed_runs: 1,
          cost_per_successful_plan: null,
        },
        trace_metrics: [],
        trace_metrics_available: false,
      },
    }),
  );
  await page.goto('/settings');
  await expect(page.getByText('Planner steps', { exact: true })).toBeVisible();
  await expect(page.getByText('Not available', { exact: true })).toBeVisible();
  await expect(
    page.getByText('Token, latency and retry metrics have not been recorded yet.'),
  ).toBeVisible();
  await expect(page.getByText('1 failed runs', { exact: true })).toBeVisible();
});

test('HTTP planner polls running, shows the published question and handles at_limit', async ({
  page,
}) => {
  let polls = 0;
  let answered = false;
  let continued = false;
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
    const question = continued || (!answered && polls > 1);
    return route.fulfill({
      json: {
        ...wireRun,
        status: question ? 'waiting_for_user' : answered ? 'at_limit' : 'running',
        steps: [
          {
            n: 1,
            tool: question ? 'ask-user' : 'search-memory',
            text: question
              ? continued
                ? 'Which venue should we use?'
                : 'Will there be prizes?'
              : 'Read the approved notes',
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
  await page.route('**/api/runs/run-wire-example/continue', (route) => {
    expect(route.request().method()).toBe('POST');
    expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
    continued = true;
    return route.fulfill({ json: { ...wireRun, status: 'running', steps: [] } });
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
  await page.getByRole('button', { name: 'Continue planning', exact: true }).click();
  await expect(page.getByPlaceholder('Your answer')).toBeVisible();
  await expect(page.locator('.agent-question')).toContainText('Which venue should we use?');
});

test('HTTP stop leaves a limited run paused without sending an unsupported action', async ({
  page,
}) => {
  let writes = 0;
  page.on('request', (request) => {
    if (request.url().includes('/api/') && request.method() !== 'GET') writes++;
  });
  await page.route('**/api/runs/run-paused-example', (route) =>
    route.fulfill({
      json: {
        run_id: 'run-paused-example',
        club_id: 'running-club',
        event_id: null,
        status: 'at_limit',
        steps: [],
        steps_used: 8,
        step_limit: 8,
        cost_usd: '0.05',
        cost_limit_usd: '0.05',
      },
    }),
  );
  await page.route('**/api/events', (route) => route.fulfill({ json: [] }));
  await page.goto('/events/new?run=run-paused-example');
  await page.getByRole('button', { name: 'Stop here', exact: true }).click();
  await expect(page).toHaveURL(/\/events$/);
  expect(writes).toBe(0);
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
