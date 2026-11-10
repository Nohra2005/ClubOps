import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { createWorkspace } from '../src/api/fixtures';

test('starter checklist completes in the synthetic workspace and persists metadata without approving facts', async ({
  page,
}) => {
  const workspace = createWorkspace('asme');
  workspace.setup_index = 10;
  workspace.setup_complete = true;
  await page.addInitScript((workspace) => {
    localStorage.setItem('clubops.demo.workspace.v1.asme', JSON.stringify(workspace));
    localStorage.setItem(
      'clubops.demo.session.v1',
      JSON.stringify({ club: 'asme', role: 'president' }),
    );
  }, workspace);
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  const checklist = page.getByRole('region', { name: "Your club's starter checklist" });
  await expect(checklist).toContainText('0 of 4');
  await page.getByLabel('I have checked the cabinet list').check();
  await page.getByLabel('Club rules or constitution file').setInputFiles({
    name: 'constitution.md',
    mimeType: 'text/plain',
    buffer: Buffer.from('Synthetic constitution'),
  });
  await checklist.getByRole('button', { name: 'Upload club rules for Review' }).click();
  await page.getByLabel('Past proposal file').setInputFiles({
    name: 'proposal.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Synthetic past proposal'),
  });
  await checklist.getByRole('button', { name: 'Upload past proposal for Review' }).click();
  await page
    .getByLabel('I have checked places and partners, including anything still unknown')
    .check();
  await expect(checklist).toContainText('4 of 4');
  const saved = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('clubops.demo.workspace.v1.asme')!),
  );
  expect(saved.review.every((card: { status: string }) => card.status === 'pending')).toBe(true);
  expect(
    saved.knowledge
      .filter((item: { tab: string; status: string }) => item.tab === 'documents')
      .every((item: { status: string }) => item.status !== 'current'),
  ).toBe(true);
  await expect(page.locator('body')).toHaveJSProperty(
    'scrollWidth',
    await page.evaluate(() => document.body.clientWidth),
  );
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(results.violations).toEqual([]);
  await page.reload();
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await expect(checklist).toContainText('4 of 4');
});

test('new-club setup is skippable and leaves learned facts unapproved', async ({ page }) => {
  await page.goto('/events');
  await page.getByLabel('Club', { exact: true }).selectOption('asme');
  await expect(page).toHaveURL(/\/setup$/);
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await page.getByLabel('Your setup answer').fill('Synthetic club: monthly design workshops.');
  await page.getByRole('button', { name: 'Next question', exact: true }).click();
  for (let i = 0; i < 9; i++)
    await page.getByRole('button', { name: 'Skip this question', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Your club interview is complete.' }),
  ).toBeVisible();
  await expect(page.getByText('none were approved here.', { exact: false })).toBeVisible();
  const workspace = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('clubops.demo.workspace.v1.asme')!),
  );
  expect(
    workspace.review.some(
      (r: { status: string; statement: string }) =>
        r.status === 'pending' && r.statement.includes('monthly design workshops'),
    ),
  ).toBe(true);
  expect(
    workspace.knowledge.some((r: { statement: string }) =>
      r.statement.includes('monthly design workshops'),
    ),
  ).toBe(false);
  await page.getByRole('link', { name: 'Review what we learned' }).click();
  await expect(
    page.getByRole('heading', { name: 'Synthetic club: monthly design workshops.', exact: true }),
  ).toBeVisible();
});

test('setup progress resumes after leaving and reloading', async ({ page }) => {
  await page.goto('/events');
  await page.getByLabel('Club', { exact: true }).selectOption('asme');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await page.getByLabel('Your setup answer').fill('Synthetic design society.');
  await page.getByRole('button', { name: 'Next question', exact: true }).click();
  await expect(page.locator('.setup-progress')).toContainText('2 of 10');
  await page.getByRole('button', { name: /Stop for now/ }).click();
  await expect(page).toHaveURL(/\/events$/);
  await page.reload();
  await expect(page).toHaveURL(/\/events$/);
  await page.goto('/setup');
  await page.getByRole('button', { name: 'Start or resume club setup' }).click();
  await expect(page.locator('.setup-progress')).toContainText('2 of 10');
  await expect(page.getByLabel('Your setup answer')).toHaveValue('');
});
