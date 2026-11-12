/** These tests use the real HTTP adapter with intercepted synthetic responses, not a deployed API. */
import { expect, test } from '@playwright/test';
import { clubs, createWorkspace } from '../src/api/fixtures';
import { todayInBeirut } from '../src/lib';

test('HTTP C-35 stays unavailable without requesting unpublished inbox or lifecycle endpoints', async ({
  page,
}) => {
  const unexpected: string[] = [];
  await page.route('**/api/**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/me') return route.fallback();
    if (path === '/api/knowledge' || path === '/api/review') return route.fulfill({ json: [] });
    unexpected.push(`${route.request().method()} ${path}`);
    return route.fulfill({ status: 501, json: { detail: 'Unpublished route' } });
  });
  await page.goto('/inbox');
  await expect(
    page.getByText('Inbox integration is not available yet.', { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /Read this|Confirm simulated read/ })).toHaveCount(
    0,
  );
  await page.goto('/setup');
  await expect(page.getByRole('region', { name: 'Forwarding setup' })).toContainText(
    'not available on this server yet',
  );
  await expect(page.getByLabel('Sample sending address')).toHaveCount(0);
  await page.goto('/review');
  await expect(page.getByRole('region', { name: 'Deadline lifecycle preview' })).toHaveCount(0);
  expect(unexpected).toEqual([]);
});

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

test('HTTP setup resumes durable progress and recovers a queue failure without resending an answer', async ({
  page,
}) => {
  await page.route('**/api/knowledge?**', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/events', (route) => route.fulfill({ json: [] }));
  let position = 3;
  let answers = 0;
  await page.route('**/api/setup/next', async (route) => {
    expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
    const body = route.request().postDataJSON();
    if (body.answer !== undefined) {
      answers++;
      expect(body).toEqual({ answer: 'Synthetic venue lesson.' });
      position = 4; // extraction was saved, but its queue completion response failed
      await route.fulfill({ status: 503, json: { detail: 'Synthetic internal error' } });
    } else
      await route.fulfill({
        json: {
          question: `Synthetic question ${position}`,
          index: position,
          total: 10,
          done: false,
          rules_count: 0,
        },
      });
  });
  await page.goto('/setup');
  await expect(
    page.getByText('No approved shared rules are available yet.', { exact: false }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await expect(page.locator('.setup-progress')).toContainText('3 of 10');
  await page.getByLabel('Your setup answer').fill('Synthetic venue lesson.');
  await page.getByRole('button', { name: 'Next question', exact: true }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByLabel('Your setup answer')).toHaveValue('Synthetic venue lesson.');
  await page.getByRole('button', { name: 'Resume saved setup' }).click();
  await expect(page.locator('.setup-progress')).toContainText('4 of 10');
  expect(answers).toBe(1);
  await page.getByRole('button', { name: /Stop for now/ }).click();
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await expect(page.locator('.setup-progress')).toContainText('4 of 10');
});

test('an incompatible setup response preserves the draft and allows an explicit retry', async ({
  page,
}) => {
  await page.route('**/api/knowledge?**', (route) => route.fulfill({ json: [] }));
  let invalid = true;
  await page.route('**/api/setup/next', async (route) => {
    const body = route.request().postDataJSON();
    const index = body.answer === undefined ? 1 : invalid ? 0 : 2;
    if (body.answer !== undefined) invalid = false;
    await route.fulfill({
      json: { question: 'Synthetic setup question', index, total: 10, done: false, rules_count: 0 },
    });
  });
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await page.getByLabel('Your setup answer').fill('Synthetic unsaved answer.');
  await page.getByRole('button', { name: 'Next question', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('incompatible data');
  await expect(page.getByLabel('Your setup answer')).toHaveValue('Synthetic unsaved answer.');
  await page.getByRole('button', { name: 'Next question', exact: true }).click();
  await expect(page.locator('.setup-progress')).toContainText('2 of 10');
  await expect(page.getByLabel('Your setup answer')).toHaveValue('');
});

test('an adviser cannot open the setup controls or post setup answers', async ({ page }) => {
  let changes = 0;
  await page.route('**/api/me', (route) =>
    route.fulfill({
      json: {
        user: {
          member_id: 'm-adviser',
          name: 'Synthetic Adviser',
          email: 'adviser@example.com',
          role: 'adviser',
        },
        role: 'adviser',
        club: clubs[0],
        counts: { overdue_events: 0, review: 0, reminders: 0 },
      },
    }),
  );
  await page.route('**/api/events', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/knowledge?**', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/setup/next', (route) => {
    changes++;
    return route.fulfill({ status: 403, json: {} });
  });
  await page.goto('/setup');
  await expect(page).toHaveURL(/\/events$/);
  await expect(page.getByRole('button', { name: 'Start or resume club setup' })).toHaveCount(0);
  expect(changes).toBe(0);
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
  await expect(page.getByRole('button', { name: 'Sign in locally' })).toHaveCount(0);
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
    { ...example, id: 'shared-fact', title: 'Synthetic shared fact', shared: true },
    {
      ...example,
      id: 'disputed-fact',
      type: 'disagreement' as const,
      title: 'Synthetic disputed fact',
    },
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

test('starter checklist uploads require confirmation, reject failed acknowledgements and preserve retry files', async ({
  page,
}) => {
  const workspace = createWorkspace('running-club');
  await page.route('**/api/knowledge?*', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/cabinet', (route) => route.fulfill({ json: workspace.members }));
  await page.route('**/api/setup/next', (route) =>
    route.fulfill({
      json: { question: 'Synthetic done', index: 10, total: 10, done: true, rules_count: 27 },
    }),
  );
  let uploads = 0;
  await page.route('**/api/documents', (route) => {
    uploads++;
    expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
    expect(route.request().postDataBuffer()?.toString()).toContain('Synthetic source');
    if (uploads === 1) return route.fulfill({ json: { detail: 'Not a document acknowledgement' } });
    if (uploads === 2) return route.fulfill({ status: 503, json: { detail: 'Synthetic failure' } });
    return route.fulfill({ json: { item_id: 'kh-synthetic-document', tab: 'documents' } });
  });
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  const checklist = page.getByRole('region', { name: "Your club's starter checklist" });
  await expect(checklist).toContainText('0 of 4');
  const file = checklist.getByLabel('Club rules or constitution file');
  await file.setInputFiles({
    name: 'synthetic-rules.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Synthetic source'),
  });
  expect(uploads).toBe(0);
  const send = checklist.getByRole('button', { name: 'Upload club rules for Review' });
  await send.evaluate((button) => {
    (button as HTMLButtonElement).click();
    (button as HTMLButtonElement).click();
  });
  await expect(checklist.getByRole('alert')).toContainText('server did not confirm');
  await expect(file).toHaveValue(/synthetic-rules.txt$/);
  await expect(checklist).toContainText('0 of 4');
  await send.click();
  await expect(checklist.getByRole('alert')).toBeVisible();
  await expect(checklist).toContainText('0 of 4');
  await send.click();
  await expect(checklist).toContainText('1 of 4');
  expect(uploads).toBe(3);
  await expect(checklist).toContainText('contents still need Review');
  await page.reload();
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await expect(checklist).toContainText('1 of 4');
  expect(uploads).toBe(3);
  const ticks = await page.evaluate(() =>
    Object.entries(localStorage)
      .filter(([key]) => key.startsWith('clubops.starter.v1.'))
      .map(([, value]) => value),
  );
  expect(ticks.join('')).not.toContain('synthetic-rules');
  expect(ticks.join('')).not.toContain('Synthetic source');
});

test('starter cabinet action uses the existing API and local checks do not call learning', async ({
  page,
}) => {
  const workspace = createWorkspace('running-club');
  let members = workspace.members;
  let added = 0;
  let learned = 0;
  await page.route('**/api/knowledge?*', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/calendar?*', (route) =>
    route.fulfill({ json: { connected: false, items: [] } }),
  );
  await page.route('**/api/usage', (route) => route.fulfill({ json: workspace.usage }));
  await page.route('**/api/cabinet', (route) => {
    if (route.request().method() === 'POST') {
      added++;
      expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
      const member = { ...route.request().postDataJSON(), member_id: 'm-starter-example' };
      members = [...members, member];
      return route.fulfill({ json: member });
    }
    return route.fulfill({ json: members });
  });
  await page.route('**/api/setup/next', (route) =>
    route.fulfill({
      json: { question: 'Synthetic done', index: 10, total: 10, done: true, rules_count: 27 },
    }),
  );
  await page.route('**/api/chat/teach', (route) => {
    learned++;
    return route.fulfill({ status: 500 });
  });
  await page.route('**/api/documents', (route) => {
    learned++;
    return route.fulfill({ status: 500 });
  });
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await page.getByRole('link', { name: 'Add or check cabinet members' }).click();
  await expect(page).toHaveURL(/\/settings#cabinet$/);
  await page.getByRole('button', { name: 'Add member', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Name', { exact: true }).fill('Synthetic Starter Member');
  await dialog.getByLabel('Email', { exact: true }).fill('starter@example.com');
  await dialog.getByRole('button', { name: 'Add member', exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(added).toBe(1);
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await page.getByLabel('I have checked the cabinet list').check();
  await page
    .getByLabel('I have checked places and partners, including anything still unknown')
    .check();
  await expect(page.getByRole('region', { name: "Your club's starter checklist" })).toContainText(
    '2 of 4',
  );
  expect(learned).toBe(0);
});

test('starter cabinet confirmation waits for a valid server list', async ({ page }) => {
  const workspace = createWorkspace('running-club');
  let valid = false;
  await page.route('**/api/knowledge?*', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/cabinet', (route) =>
    route.fulfill({ json: valid ? workspace.members : { detail: 'Synthetic malformed list' } }),
  );
  await page.route('**/api/setup/next', (route) =>
    route.fulfill({
      json: { question: 'Synthetic done', index: 10, total: 10, done: true, rules_count: 27 },
    }),
  );
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  const checklist = page.getByRole('region', { name: "Your club's starter checklist" });
  await expect(checklist.getByRole('alert')).toContainText('server did not return a cabinet list');
  await expect(checklist.getByLabel('I have checked the cabinet list')).toHaveCount(0);
  await expect(checklist).toContainText('0 of 4');
  valid = true;
  await checklist.getByRole('button', { name: 'Try again', exact: true }).click();
  await checklist.getByLabel('I have checked the cabinet list').check();
  await expect(checklist).toContainText('1 of 4');
});

test('shared review shows comparison quotes, prioritizes disagreements and sends the president choice', async ({
  page,
}) => {
  const [fact, merge, conflict] = ['fact', 'merge', 'disagreement'].map((type) =>
    createWorkspace('running-club').review.find((card) => card.type === type)!,
  );
  let cards = [
    { ...fact, id: 'private-example', shared: false, source: { ...fact.source, quote: undefined } },
    {
      ...merge,
      id: 'shared-merge',
      shared: true,
      source: { ...merge.source, quote: 'Synthetic proposed quote <script>untrusted()</script>' },
      alternative: {
        ...merge.alternative!,
        source: { ...merge.alternative!.source, quote: 'Synthetic existing quote' },
      },
    },
    { ...conflict, id: 'first-conflict', shared: false },
  ];
  const decisions: Record<string, unknown>[] = [];
  await page.route('**/api/review?*', (route) => route.fulfill({ json: cards }));
  await page.route('**/api/review/*', (route) => {
    const payload = route.request().postDataJSON();
    expect(route.request().headers()['x-requested-with']).toBe('ClubOps');
    decisions.push(payload);
    const result = { ...cards[1], status: 'approved' };
    cards = cards.filter((card) => card.id !== 'shared-merge');
    return route.fulfill({ json: result });
  });
  await page.goto('/review');
  await expect(page.locator('.review-card').first()).toHaveAttribute('id', 'first-conflict');
  const card = page.locator('#shared-merge');
  await expect(card.getByText('Shared with all AUB clubs', { exact: true })).toBeVisible();
  await expect(card.getByRole('blockquote')).toHaveCount(2);
  await expect(
    card.getByText('Synthetic proposed quote <script>untrusted()</script>', { exact: true }),
  ).toBeVisible();
  await expect(page.locator('script').filter({ hasText: 'untrusted()' })).toHaveCount(0);
  await expect(page.locator('#private-example')).toContainText('No source quote supplied.');
  await card.getByRole('switch').uncheck();
  expect(decisions).toEqual([]);
  await card.getByRole('button', { name: 'Merge', exact: true }).click();
  await expect(card).toHaveCount(0);
  expect(decisions[0]).toMatchObject({ decision: 'merge', shared: false });
});

test('a non-president cannot decide shared facts or change sharing and private decisions omit the override', async ({
  page,
}) => {
  const workspace = createWorkspace('running-club');
  await page.route('**/api/me', (route) =>
    route.fulfill({
      json: {
        user: workspace.members[0],
        role: 'secretary',
        club: clubs[0],
        counts: { overdue_events: 0, review: 0, reminders: 0 },
      },
    }),
  );
  const example = workspace.review.find((card) => card.type === 'fact')!;
  let cards = [
    { ...example, id: 'shared-fact', shared: true },
    { ...example, id: 'private-fact', shared: false },
  ];
  const requests: Record<string, unknown>[] = [];
  await page.route('**/api/review?*', (route) => route.fulfill({ json: cards }));
  await page.route('**/api/review/*', (route) => {
    requests.push(route.request().postDataJSON());
    cards = cards.filter((card) => card.id !== 'private-fact');
    return route.fulfill({ json: { ...example, status: 'approved' } });
  });
  await page.goto('/review');
  await expect(page.locator('#shared-fact').getByRole('button')).toHaveCount(0);
  await expect(page.getByRole('switch')).toHaveCount(0);
  await page.locator('#private-fact').getByRole('button', { name: 'Approve', exact: true }).click();
  await expect(page.locator('#private-fact')).toHaveCount(0);
  expect(requests).toHaveLength(1);
  expect(requests[0]).not.toHaveProperty('shared');
});

test('a rejected sharing decision preserves edits and the choice until a deliberate retry', async ({
  page,
}) => {
  const example = createWorkspace('running-club').review.find((card) => card.type === 'fact')!;
  let pending = true;
  const requests: Record<string, unknown>[] = [];
  await page.route('**/api/review?*', (route) =>
    route.fulfill({ json: pending ? [{ ...example, id: 'retry-fact', shared: false }] : [] }),
  );
  await page.route('**/api/review/*', (route) => {
    requests.push(route.request().postDataJSON());
    if (requests.length === 1)
      return route.fulfill({ status: 403, json: { detail: 'Synthetic server refusal' } });
    pending = false;
    return route.fulfill({ json: { ...example, status: 'approved', shared: true } });
  });
  await page.goto('/review');
  const card = page.locator('#retry-fact');
  await card.getByRole('switch').check();
  await expect(page.getByRole('button', { name: 'Approve all facts', exact: true })).toHaveCount(0);
  expect(requests).toHaveLength(0);
  await card.getByRole('button', { name: 'Edit then approve' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Proposed statement').fill('Synthetic edited fact.');
  await dialog.getByRole('button', { name: 'Confirm decision' }).click();
  await expect(dialog.getByRole('alert')).toBeVisible();
  await expect(dialog.getByLabel('Proposed statement')).toHaveValue('Synthetic edited fact.');
  await dialog.getByRole('button', { name: 'Confirm decision' }).click();
  await expect(card).toHaveCount(0);
  expect(requests).toHaveLength(2);
  expect(
    requests.every(
      (request) => request.shared === true && request.edited_text === 'Synthetic edited fact.',
    ),
  ).toBe(true);
});
