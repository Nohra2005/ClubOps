import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testIgnore: [
    'contracts.spec.ts',
    'role-learning.spec.ts',
    'session-http.spec.ts',
    'inbox-actions.spec.ts',
    'restore-http.spec.ts',
    'live-api.spec.ts',
    'local-login.spec.ts',
    'setup-live.spec.ts',
    'routing.spec.ts',
    'demo-rehearsal.spec.ts',
  ],
  fullyParallel: true,
  workers: 2,
  timeout: 35_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    channel:
      process.env.PLAYWRIGHT_CHANNEL === 'bundled'
        ? undefined
        : (process.env.PLAYWRIGHT_CHANNEL ?? 'chrome'),
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    {
      name: 'phone',
      use: {
        ...devices['iPhone 13'],
        defaultBrowserType: 'chromium',
        viewport: { width: 375, height: 812 },
      },
    },
  ],
  webServer: {
    command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
  },
});
