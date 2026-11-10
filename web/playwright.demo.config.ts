import { defineConfig } from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testIgnore: [],
  testMatch: 'demo-rehearsal.spec.ts',
  grep: /rehearses the five-minute demo/,
  timeout: 390_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  outputDir: `../output/demo-rehearsal-${Date.now()}-${process.pid}`,
  projects: [{ name: 'recording', use: { viewport: { width: 1440, height: 1000 } } }],
  use: {
    ...base.use,
    baseURL: 'http://127.0.0.1:5176',
    serviceWorkers: 'block',
    acceptDownloads: false,
    video: { mode: 'on', size: { width: 1440, height: 1000 } },
    trace: 'off',
  },
  webServer: {
    command: 'npm run dev -- --port 5176 --strictPort',
    url: 'http://127.0.0.1:5176',
    env: {
      VITE_API_MODE: 'http',
      VITE_API_BASE: '/api',
      VITE_GOOGLE_CLIENT_ID: '',
      VITE_DEV_LOGIN: '0',
    },
    reuseExistingServer: false,
  },
});
