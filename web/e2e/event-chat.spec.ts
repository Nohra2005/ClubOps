import { expect, test } from '@playwright/test';

test('F-513: event conversations and General stay separate and can be reopened', async ({
  page,
}) => {
  await page.goto('/chat');
  const spaces = page.getByRole('navigation', { name: 'Chat spaces' });
  const history = page.getByRole('navigation', { name: 'Conversations' });
  const ask = async (text: string) => {
    await page.getByLabel('Ask your club', { exact: true }).fill(text);
    await page.getByRole('button', { name: 'Ask ClubOps' }).click();
  };
  const transcript = page.locator('.chat-messages');
  const openHistory = async () => {
    const toggle = page.getByRole('button', { name: 'Chat history' });
    if ((await toggle.isVisible()) && (await toggle.getAttribute('aria-expanded')) === 'false') {
      await toggle.click();
    }
  };
  const openSpace = async (name: string) => {
    await openHistory();
    await spaces.getByRole('link', { name, exact: true }).click();
    await page.locator('.chat-scope-heading h2').getByText(name, { exact: true }).waitFor();
    await openHistory();
  };

  await ask('What did we learn from the last run?');
  await expect(transcript).toContainText('Welcome run debrief');
  await openSpace('Sunset campus run');
  await expect(history.getByText('No conversations yet')).toBeVisible();
  await ask('When is this event?');
  await expect(transcript).toContainText('Sunset campus run starts on');
  await expect(transcript.getByRole('link', { name: 'Event details' })).toHaveAttribute(
    'href',
    '/events/ev-sunset-run',
  );
  await ask('Can you repeat that?');
  await expect(transcript.getByText(/Sunset campus run starts on/)).toHaveCount(2);

  await page.getByRole('button', { name: 'New chat' }).click();
  await ask('Where is it?');
  await expect(transcript).toContainText('Sunset campus run is scheduled at');
  await expect(history.getByRole('button')).toHaveCount(2);

  await openSpace('Welcome run');
  await expect(history.getByText('No conversations yet')).toBeVisible();
  await openSpace('General');
  await expect(transcript).toContainText('Welcome run debrief');
  await expect(history.getByRole('button')).toHaveCount(1);
  await openSpace('Sunset campus run');
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Sunset campus run', exact: true })).toBeVisible();
  await openHistory();
  await history.getByRole('button', { name: 'When is this event?' }).click();
  await expect(transcript.getByText(/Sunset campus run starts on/)).toHaveCount(2);
});

test('an event opens a fresh conversation and an unknown event has no composer', async ({
  page,
}) => {
  await page.goto('/events/ev-sunset-run');
  await page.getByRole('link', { name: 'Event chat' }).click();
  await expect(page.getByRole('heading', { name: 'Ask about Sunset campus run' })).toBeVisible();
  await page.goto('/chat?event=unavailable-event');
  await expect(page.getByText('This event is unavailable.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ask ClubOps' })).toHaveCount(0);
});
