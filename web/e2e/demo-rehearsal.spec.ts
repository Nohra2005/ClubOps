/** C-28 UI screenplay only: every API reply is synthetic, no backend defense is measured. */
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';
import { caption, DISCLOSURE, installRehearsal } from '../demo/browser';
import {
  ANSWER,
  CARD_ID,
  DENIED_ID,
  DESCRIPTION,
  DOCUMENT,
  FILE_NAME,
  LIMIT_ID,
} from '../demo/scenario';

test('rehearses the five-minute demo with explicit fixture provenance', async ({
  page,
  context,
  baseURL,
}, info) => {
  const recording = info.project.name === 'recording';
  const fixture = await installRehearsal(context, baseURL!);
  const chapters: { id: string; passed: boolean }[] = [];
  const video = page.video();
  let activeCaption = '';
  async function go(path: string) {
    await page.goto(path);
    await caption(page, activeCaption);
  }
  async function narrate(seconds: number) {
    if (recording) await page.waitForTimeout(seconds * 1000);
  }
  async function chapter(id: string, text: string, seconds: number, action: () => Promise<void>) {
    const started = Date.now();
    activeCaption = text;
    await action();
    await caption(page, text);
    await expect(page.getByLabel('Rehearsal disclosure')).toContainText(DISCLOSURE);
    chapters.push({ id, passed: true });
    if (recording) await page.waitForTimeout(Math.max(0, seconds * 1000 - (Date.now() - started)));
  }

  await chapter(
    'context',
    '00:00–00:30 · Synthetic local UI rehearsal; no real club or provider.',
    30,
    async () => {
      await go('/events');
      await expect(page.getByRole('heading', { name: 'Events', exact: true })).toBeVisible();
      await expect(page.getByText('Synthetic Demo Club', { exact: false }).first()).toBeVisible();
      await expect(page.locator('.demo-strip')).toHaveCount(0); // use real HTTP adapter, not demo cache
      expect(await context.cookies()).toEqual([]);
    },
  );

  await chapter(
    'plan-question-approval',
    '00:30–01:50 · Scripted missing-room question; explicit human approval.',
    80,
    async () => {
      await go('/events/new');
      await page.getByLabel('Describe your event').fill(DESCRIPTION);
      expect(fixture.scene.counts.plans).toBe(0);
      await page.getByRole('button', { name: 'Plan it', exact: true }).click();
      await expect(page.getByPlaceholder('Your answer')).toBeVisible();
      await expect(page.locator('.agent-question')).toContainText('Which room should we use?');
      await narrate(20);
      expect(fixture.scene.counts.approvals).toBe(0);
      await page.getByPlaceholder('Your answer').fill(ANSWER);
      await page.getByRole('button', { name: 'Answer and continue' }).click();
      await expect(page.getByRole('button', { name: 'Approve plan', exact: true })).toBeVisible();
      await expect(
        page.getByText('Synthetic checklist; not AUB policy', { exact: true }).first(),
      ).toBeVisible();
      expect(fixture.scene.counts.approvals).toBe(0);
      await narrate(15);
      await page.getByRole('button', { name: 'Approve plan', exact: true }).click();
      await expect(
        page.getByText('Approved by Synthetic President', { exact: true }),
      ).toBeVisible();
      expect(fixture.scene.counts.approvals).toBe(1);
    },
  );

  await chapter(
    'limit',
    '01:50–02:35 · Scripted eight-step limit; Stop leaves it paused.',
    45,
    async () => {
      await go(`/events/new?run=${LIMIT_ID}`);
      await expect(page.getByText('This run reached its limit.', { exact: true })).toBeVisible();
      await expect(
        page.getByRole('button', { name: 'Continue planning', exact: true }),
      ).toBeVisible();
      await expect(page.getByRole('button', { name: 'Approve plan', exact: true })).toHaveCount(0);
      await narrate(20);
      await page.getByRole('button', { name: 'Stop here', exact: true }).click();
      await expect(page).toHaveURL(/\/events$/);
      expect(fixture.scene.counts.plans).toBe(1);
    },
  );

  await chapter(
    'untrusted-document',
    '02:35–03:40 · Fixture supplies a warning; UI keeps it out of bulk approval.',
    65,
    async () => {
      await go('/settings');
      await page.getByLabel('Upload source document').setInputFiles({
        name: FILE_NAME,
        mimeType: 'text/plain',
        buffer: Buffer.from(DOCUMENT),
      });
      const uploaded = page.getByRole('link', { name: FILE_NAME, exact: true });
      await expect(uploaded).toBeVisible();
      await uploaded.scrollIntoViewIfNeeded();
      expect(fixture.scene.counts.uploads).toBe(1);
      await narrate(10);
      await go('/review');
      const card = page.locator(`#${CARD_ID}`);
      await expect(card).toContainText('Source contains hidden instructions');
      await expect(card.locator('blockquote')).toContainText('Ignore previous instructions');
      await card.scrollIntoViewIfNeeded();
      await expect(
        page.getByRole('button', { name: 'Approve all facts', exact: true }),
      ).toHaveCount(0);
      await narrate(25);
      await card.getByRole('button', { name: 'Reject', exact: true }).click();
      await page
        .getByLabel('Reason (optional)')
        .fill('Synthetic rehearsal: reject the injected instruction.');
      await page
        .getByRole('dialog')
        .getByRole('button', { name: 'Reject proposal', exact: true })
        .click();
      await expect(page.getByRole('heading', { name: 'Nothing to review.' })).toBeVisible();
      expect(fixture.scene.counts.rejections).toBe(1);
    },
  );

  await chapter(
    'restricted-role',
    '03:40–04:25 · Read-only UI + scripted HTTP 403; not a backend authorization test.',
    45,
    async () => {
      fixture.scene.setAdviser();
      await go(`/events/${DENIED_ID}`);
      await expect(page.locator('.read-only-strip')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Approve plan', exact: true })).toHaveCount(0);
      await narrate(15);
      // A deliberate adversarial browser request to our intercepted fixture only.
      const status = await page.evaluate(
        async (id) =>
          (
            await fetch(`/api/events/${id}/approve-plan`, {
              method: 'POST',
              headers: { 'X-Requested-With': 'ClubOps', 'Content-Type': 'application/json' },
              body: JSON.stringify({ revision: 1 }),
            })
          ).status,
        DENIED_ID,
      );
      expect(status).toBe(403);
      expect(fixture.scene.respond('GET', `/events/${DENIED_ID}`).json).toMatchObject({
        status: 'planned',
      });
      expect(fixture.scene.counts.approvals).toBe(1);
    },
  );

  await chapter(
    'limits-and-next',
    '04:25–05:00 · Real deployment, model/defense evidence, team rehearsal and narration remain pending.',
    35,
    async () => {
      await go('/events');
      await expect(page.getByRole('heading', { name: 'Events', exact: true })).toBeVisible();
      expect(fixture.violations).toEqual([]);
      expect(fixture.requestCount()).toBeGreaterThan(0);
      expect(fixture.scene.counts).toEqual({
        plans: 1,
        answers: 1,
        approvals: 1,
        uploads: 1,
        rejections: 1,
        denied: 1,
      });
    },
  );
  await page.screenshot({ path: info.outputPath('rehearsal-summary.png') });
  await context.close(); // finish the isolated recording before hashing/saving it
  let recordingProof: { file: string; sha256: string; bytes: number } | null = null;
  if (recording) {
    expect(video, 'Recording mode must produce a video.').toBeTruthy();
    const file = 'backup-rehearsal.webm';
    await video!.saveAs(info.outputPath(file));
    const bytes = await readFile(info.outputPath(file));
    expect(bytes.length).toBeGreaterThan(1000);
    recordingProof = {
      file,
      sha256: createHash('sha256').update(bytes).digest('hex'),
      bytes: bytes.length,
    };
  }
  await writeFile(
    info.outputPath('rehearsal-proof.json'),
    JSON.stringify(
      {
        task: 'C-28',
        kind: 'synthetic HTTP/UI rehearsal; not deployed or backend/model/security evidence',
        disclosure: DISCLOSURE,
        chapters,
        fixture_requests: fixture.requestCount(),
        actions: fixture.scene.counts,
        unexpected_requests: fixture.violations.length,
        recording: recordingProof,
        final_acceptance:
          'pending deployed run, backend defenses, team rehearsal and narrated final backup',
      },
      null,
      2,
    ) + '\n',
  );
});

test('blocks external requests and refuses unscripted API actions', async ({
  page,
  context,
  baseURL,
}) => {
  const fixture = await installRehearsal(context, baseURL!);
  await page.goto('/events');
  await expect(page.getByRole('heading', { name: 'Events', exact: true })).toBeVisible();
  const status = await page.evaluate(
    async () => (await fetch('/api/unregistered-rehearsal-action')).status,
  );
  expect(status).toBe(501);
  const blocked = await page.evaluate(async () => {
    try {
      await fetch('https://rehearsal-egress.invalid/probe');
      return false;
    } catch {
      return true;
    }
  });
  expect(blocked).toBe(true);
  expect(fixture.violations).toEqual(['Unregistered API action.', 'External request blocked.']);
  expect(fixture.scene.counts.plans).toBe(0);
});
