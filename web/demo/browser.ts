import type { BrowserContext, Page } from '@playwright/test';
import { RehearsalScenario, validateLocalOrigin } from './scenario';

export const DISCLOSURE =
  'SCRIPTED REHEARSAL · synthetic HTTP fixtures · no backend or model calls';

/** Only a new Playwright context is supported; never connect to a person's browser. */
export async function installRehearsal(context: BrowserContext, baseURL: string) {
  const origin = validateLocalOrigin(baseURL);
  const scene = new RehearsalScenario();
  const violations: string[] = [];
  let requests = 0;
  await context.routeWebSocket('**/*', (socket) => socket.close());
  await context.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== origin) {
      violations.push('External request blocked.');
      await route.abort('blockedbyclient');
      return;
    }
    if (url.pathname !== '/api' && !url.pathname.startsWith('/api/')) {
      await route.continue();
      return;
    }
    requests++;
    const contentType = request.headers()['content-type'] ?? '';
    let body: unknown;
    try {
      body = contentType.includes('application/json') ? request.postDataJSON() : request.postData();
    } catch {
      violations.push('Invalid request body.');
    }
    const reply = scene.respond(
      request.method(),
      url.pathname.slice(4) + url.search,
      body,
      request.headers()['x-requested-with'],
    );
    if (reply.status === 501) violations.push('Unregistered API action.');
    await route.fulfill({ status: reply.status, json: reply.json });
  });
  await context.addInitScript(
    ({ text }) => {
      document.addEventListener('DOMContentLoaded', () => {
        const banner = document.createElement('aside');
        banner.id = 'c28-rehearsal-disclosure';
        banner.setAttribute('aria-label', 'Rehearsal disclosure');
        banner.style.cssText =
          'position:fixed;bottom:0;left:0;right:0;z-index:2147483647;' +
          'background:#172a3a;color:white;padding:10px 16px;font:600 12px/1.4 sans-serif;pointer-events:none';
        banner.textContent = text;
        document.body.append(banner);
        document.body.style.paddingBottom = '70px';
      });
    },
    { text: DISCLOSURE },
  );
  return { scene, violations, requestCount: () => requests };
}

export async function caption(page: Page, text: string) {
  await page.locator('#c28-rehearsal-disclosure').evaluate(
    (node, values) => {
      node.replaceChildren(document.createTextNode(values.disclosure));
      const detail = document.createElement('div');
      detail.style.cssText = 'font-weight:400;margin-top:3px';
      detail.textContent = values.text;
      node.append(detail);
    },
    { disclosure: DISCLOSURE, text },
  );
}
