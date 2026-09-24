// Shared Playwright fixtures for the NGJ e2e suite.
//
// Hermetic network: every request that doesn't go to the local preview server
// is intercepted — GitHub API calls get fixture JSON, avatars get a 1px PNG,
// analytics (gc.zgo.at / *.goatcounter.com) and anything else is aborted, so a
// test can never reach a real job board or tracker.
//
// Every test also fails on console errors, uncaught page errors and CSP
// violations (securitypolicyviolation events), unless it lists the console
// errors it expects via `test.use({ allowConsoleErrors: /regex/ })`.

import { test as base, expect } from '@playwright/test';
import { GH_FIXTURES, PIXEL_PNG } from './github-fixtures.js';

const LOCAL_HOSTS = new Set(['127.0.0.1', 'localhost']);
const ANALYTICS_HOST = /(^|\.)gc\.zgo\.at$|(^|\.)goatcounter\.com$/;

function githubResponse(url) {
  const path = `${url.pathname}${url.search}`;
  const hit = GH_FIXTURES.find(([pattern]) => pattern.test(path));
  return hit ? { status: 200, json: hit[1] } : { status: 404, json: { message: 'Not Found' } };
}

async function routeExternal(route, calls) {
  const url = new URL(route.request().url());
  if (LOCAL_HOSTS.has(url.hostname)) return route.fallback();
  calls.push(url.href);
  if (url.hostname === 'api.github.com') {
    const { status, json } = githubResponse(url);
    return route.fulfill({ status, json, headers: { 'access-control-allow-origin': '*' } });
  }
  if (url.hostname === 'avatars.githubusercontent.com') {
    return route.fulfill({ status: 200, contentType: 'image/png', body: PIXEL_PNG });
  }
  return route.abort('blockedbyclient');
}

/** Console errors caused by our own aborts of external hosts are expected noise. */
function isExternalAbortNoise(msg) {
  const src = msg.location() && msg.location().url;
  if (!src) return false;
  try {
    const host = new URL(src).hostname;
    return !LOCAL_HOSTS.has(host) || ANALYTICS_HOST.test(host);
  } catch {
    return false;
  }
}

export const test = base.extend({
  // A RegExp of console errors the test expects (e.g. a 404 it provokes).
  allowConsoleErrors: [null, { option: true }],

  /** Absolute URLs of every intercepted external request, in order. */
  externalCalls: async ({}, use) => { // eslint-disable-line no-empty-pattern
    await use([]);
  },

  page: async ({ page, allowConsoleErrors, externalCalls }, use, testInfo) => {
    await page.context().route('**/*', (route) => routeExternal(route, externalCalls));

    const problems = [];
    page.on('console', (msg) => {
      if (msg.type() !== 'error' || isExternalAbortNoise(msg)) return;
      const text = msg.text();
      if (allowConsoleErrors && allowConsoleErrors.test(text)) return;
      problems.push(`console.error: ${text}`);
    });
    page.on('pageerror', (err) => problems.push(`pageerror: ${err.message}`));

    await page.exposeFunction('__ngjReportCsp', (v) => problems.push(`CSP violation: ${JSON.stringify(v)}`));
    await page.addInitScript(() => {
      document.addEventListener('securitypolicyviolation', (e) => {
        window.__ngjReportCsp({ directive: e.violatedDirective, blocked: e.blockedURI, source: e.sourceFile });
      });
    });

    await use(page);

    if (problems.length) {
      await testInfo.attach('page-problems', { body: problems.join('\n'), contentType: 'text/plain' });
    }
    expect(problems, 'no console errors, page errors or CSP violations').toEqual([]);
  },
});

export { expect };
