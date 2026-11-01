import { defineConfig } from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testIgnore: [],
  testMatch: ['live-api.spec.ts', 'local-login.spec.ts'],
  // One test at a time: both browsers share this temporary, synthetic API store.
  fullyParallel: false,
  workers: 1,
  use: { ...base.use, baseURL: 'http://127.0.0.1:5175' },
  webServer: [
    {
      command: 'uv run uvicorn tests.live_web_api:build --factory --host 127.0.0.1 --port 8001',
      cwd: '..',
      url: 'http://127.0.0.1:8001/api/docs',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --port 5175 --strictPort',
      url: 'http://127.0.0.1:5175',
      env: {
        VITE_API_MODE: 'http',
        VITE_API_BASE: '/api',
        VITE_DEV_LOGIN: '1',
        CLUBOPS_API_PROXY: 'http://127.0.0.1:8001',
      },
      reuseExistingServer: false,
    },
  ],
});
