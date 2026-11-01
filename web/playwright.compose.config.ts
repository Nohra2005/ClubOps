import { defineConfig } from '@playwright/test';
import base from './playwright.config';

const baseURL = process.env.CLUBOPS_COMPOSE_URL ?? 'http://127.0.0.1:8080';
const target = new URL(baseURL);
if (target.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(target.hostname))
  throw new Error('Compose checks only run against a local development app.');

export default defineConfig({
  ...base,
  testIgnore: [],
  testMatch: ['local-login.spec.ts', 'routing.spec.ts'],
  fullyParallel: false,
  workers: 1,
  use: { ...base.use, baseURL },
  webServer: undefined,
});
