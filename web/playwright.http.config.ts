import { defineConfig } from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testIgnore: [],
  testMatch: ['contracts.spec.ts', 'demo-rehearsal.spec.ts', 'session-http.spec.ts'],
  use: { ...base.use, baseURL: 'http://127.0.0.1:5174', serviceWorkers: 'block' },
  webServer: {
    command: 'npm run dev -- --port 5174 --strictPort',
    url: 'http://127.0.0.1:5174',
    env: {
      VITE_API_MODE: 'http',
      VITE_API_BASE: '/api',
      VITE_GOOGLE_CLIENT_ID: 'synthetic.apps.googleusercontent.com',
    },
    reuseExistingServer: false,
  },
});
