import { resolve } from 'node:path';
import { defineConfig } from '@playwright/test';
import live from './playwright.live.config';

const servers = live.webServer as { command: string; cwd?: string; url: string }[];

export default defineConfig({
  ...live,
  testMatch: ['live-api.spec.ts', 'routing.spec.ts'],
  webServer: [
    servers[0],
    {
      command: `"${process.env.CADDY_BIN ?? 'caddy'}" run --config Caddyfile --adapter caddyfile`,
      url: 'http://127.0.0.1:5175',
      env: {
        PORT: '5175',
        CLUBOPS_WEB_ROOT: resolve('dist').replaceAll('\\', '/'),
        CLUBOPS_API_UPSTREAM: '127.0.0.1:8001',
      },
      reuseExistingServer: false,
    },
  ],
});
