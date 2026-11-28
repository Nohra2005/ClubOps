import { expect, test } from '@playwright/test';

test('appearance persists across routes and reloads without changing the cabinet session', async ({
  page,
}) => {
  await page.goto('/events');
  const mutations: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/') && request.method() !== 'GET')
      mutations.push(request.url());
  });
  await page.getByRole('button', { name: 'Switch to Afterdark theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'afterdark');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Switch to Frost theme' })).toBeVisible();
  await page.goto('/knowledge');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'afterdark');
  await expect(page.getByRole('heading', { name: 'Knowledge', exact: true })).toBeVisible();
  await page.goto('/login');
  await page.getByRole('button', { name: 'Switch to Frost theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'frost');
  await page.goto('/events');
  await expect(page.getByRole('heading', { name: 'Events', exact: true })).toBeVisible();
  expect(mutations).toEqual([]);
});

test('unavailable appearance storage does not prevent sign-in or theme switching', async ({
  page,
}) => {
  await page.addInitScript(() => {
    const getItem = Storage.prototype.getItem;
    const setItem = Storage.prototype.setItem;
    Storage.prototype.getItem = function (key) {
      if (key === 'clubops.theme') throw new DOMException('Synthetic blocked storage');
      return getItem.call(this, key);
    };
    Storage.prototype.setItem = function (key, value) {
      if (key === 'clubops.theme') throw new DOMException('Synthetic blocked storage');
      return setItem.call(this, key, value);
    };
  });
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Switch to Afterdark theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'afterdark');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Switch to Afterdark theme' })).toBeVisible();
});

test('malformed preferences fall back safely and a valid cross-tab change updates appearance', async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem('clubops.theme', 'invalid-theme'));
  await page.goto('/events');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'frost');
  await page.evaluate(() =>
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: 'clubops.theme',
        newValue: 'afterdark',
        storageArea: localStorage,
      }),
    ),
  );
  await expect(page.getByRole('button', { name: 'Switch to Frost theme' })).toBeVisible();
});
