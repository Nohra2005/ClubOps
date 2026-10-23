import { expect, test } from '@playwright/test';

test('adviser pages hide write actions and cabinet-only contact details', async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem(
      'clubops.demo.session.v1',
      JSON.stringify({ club: 'running-club', role: 'adviser' }),
    ),
  );
  for (const path of [
    '/events',
    '/events/ev-sunset-run',
    '/review',
    '/handover',
    '/settings',
    '/chat',
  ]) {
    await page.goto(path);
    await expect(page.locator('main h1')).toBeVisible();
    await expect(
      page.getByRole('button', {
        name: /^(Approve|Edit details|Sign off handover|Add member|Write draft|Send fact)/,
      }),
    ).toHaveCount(0);
  }
  await page.goto('/knowledge?tab=contacts');
  await expect(page.getByText('venue@example.com', { exact: false })).toHaveCount(0);
  await page.goto('/events/new');
  await expect(page).toHaveURL(/\/events$/);
});

test('an AI failure preserves the description and makes retry explicit', async ({ page }) => {
  await page.goto('/events/new?scenario=ai-error');
  const description = 'Synthetic event description that must survive a failure';
  await page.getByLabel('Describe your event').fill(description);
  await page.getByRole('button', { name: 'Plan it', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText(
    "ClubOps couldn't finish this. Nothing was saved or sent.",
  );
  await expect(page.getByLabel('Describe your event')).toHaveValue(description);
  await expect(page.getByRole('button', { name: 'Try again', exact: true })).toBeVisible();
});

test('a double click starts one paid run', async ({ page }) => {
  await page.goto('/events/new');
  await page.getByLabel('Describe your event').fill('A synthetic event with one planning request');
  await page.getByRole('button', { name: 'Plan it', exact: true }).evaluate((button) => {
    (button as HTMLButtonElement).click();
    (button as HTMLButtonElement).click();
  });
  await expect(page.getByRole('heading', { name: "Let's check the details." })).toBeVisible();
  const workspace = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('clubops.demo.workspace.v1.running-club')!),
  );
  expect(Object.keys(workspace.runs)).toHaveLength(1);
  expect(workspace.usage.calls).toBe(8);
});

test('empty and loading states give a useful next action', async ({ page }) => {
  await page.goto('/events?scenario=empty');
  await expect(page.getByRole('heading', { name: 'No events yet.' })).toBeVisible();
  await page.goto('/review?scenario=empty');
  await expect(page.getByRole('heading', { name: 'Nothing to review.' })).toBeVisible();
  await page.goto('/events?scenario=loading');
  await expect(page.locator('main h1')).toBeVisible();
  await expect(page.getByRole('status', { name: 'Loading saved information' })).toBeVisible();
  await expect(page.locator('.event-card').first()).toBeVisible();
});

test('offline errors retain edits and show the connection banner', async ({ page }) => {
  await page.goto('/events/new?scenario=offline');
  await page.getByLabel('Describe your event').fill('Keep this synthetic offline draft');
  await page.getByRole('button', { name: 'Plan it', exact: true }).click();
  await expect(page.locator('.connection-banner')).toContainText("Can't reach ClubOps");
  await expect(page.getByLabel('Describe your event')).toHaveValue(
    'Keep this synthetic offline draft',
  );
});

test('fallback answers are visibly marked as a simple version', async ({ page }) => {
  await page.goto('/chat?scenario=fallback');
  await page
    .getByLabel('Ask your club', { exact: true })
    .fill('What did we learn from the last run?');
  await page.getByRole('button', { name: 'Ask ClubOps' }).click();
  await expect(
    page.getByText('Simple version: some checks were skipped. Please review carefully.', {
      exact: true,
    }),
  ).toBeVisible();
});

test('a run limit offers an explicit stop and retains a partial draft', async ({ page }) => {
  await page.goto('/events/new?scenario=limit');
  await page.getByLabel('Describe your event').fill('A synthetic event for testing the run limit');
  await page.getByRole('button', { name: 'Plan it', exact: true }).click();
  await page.getByRole('spinbutton', { name: /Budget/ }).fill('0');
  await page.getByRole('checkbox', { name: /I checked the details/ }).check();
  await page.getByRole('button', { name: 'Confirm details', exact: true }).click();
  await expect(page.getByText('This run reached its limit.', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Continue · new run' })).toBeVisible();
  await page.getByRole('button', { name: 'Stop here', exact: true }).click();
  await expect(
    page.getByText('Stopped here. Your partial plan is saved as a draft.', { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve plan', exact: true })).toHaveCount(0);
});
