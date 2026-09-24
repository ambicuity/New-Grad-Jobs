// Playwright e2e suite for the NGJ terminal. Runs against the production
// build served by `vite preview`, with the 20-job fixture dataset copied into
// dist/ (npm run build:fixtures). Every non-local request is intercepted in
// e2e/support/test.js, so the suite is hermetic.
import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env.CI;
// NGJ_E2E_PORT lets parallel checkouts run the suite side by side.
const PORT = Number(process.env.NGJ_E2E_PORT) || 4173;
const BASE_URL = `http://127.0.0.1:${PORT}`;
const REPORT_DIR = 'playwright-report';

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: REPORT_DIR }],
    ...(isCI ? [['github']] : []),
  ],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    timezoneId: 'UTC',
    locale: 'en-US',
  },
  projects: [
    {
      name: 'desktop',
      testIgnore: /\.mobile\.spec\.js$/,
      use: { ...devices['Desktop Chrome'], viewport: { width: 1400, height: 900 } },
    },
    {
      name: 'mobile',
      testMatch: /\.mobile\.spec\.js$/,
      // Pixel 5 (touch, mobile UA) narrowed to the 375px width we design for.
      use: { ...devices['Pixel 5'], viewport: { width: 375, height: 812 } },
    },
  ],
  webServer: {
    command: `npm run build:fixtures && npm run preview -- --port ${PORT} --strictPort --host 127.0.0.1`,
    url: BASE_URL,
    // Never reuse: a server left on the port could be serving another build.
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
