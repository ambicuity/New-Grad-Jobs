// Build output outside the SPA: per-job static pages, CSP, hermetic analytics.
import { test, expect } from './support/test.js';
import { FIXTURE, expectSelected, jobList, openBoard } from './support/app.js';

test.describe('per-job static page', () => {
  test('renders the job with parseable JobPosting JSON-LD and no scripts', async ({ page }) => {
    const res = await page.goto(`/job/${FIXTURE.first}/`);
    expect(res.status()).toBe(200);

    await expect(page.getByRole('heading', { level: 1 })).toHaveText(FIXTURE.firstTitle);
    const apply = page.getByRole('link', { name: /^APPLY ON EMPLOYER SITE/ });
    await expect(apply).toHaveAttribute('href', FIXTURE.firstUrl);

    const blocks = page.locator('script[type="application/ld+json"]');
    await expect(blocks).toHaveCount(1);
    const data = JSON.parse(await blocks.textContent());
    expect(data['@context']).toMatch(/^https:\/\/schema\.org\/?$/);
    expect(data['@type']).toBe('JobPosting');
    expect(data.title).toBe(FIXTURE.firstTitle);
    expect(data.hiringOrganization.name).toBe('Palantir');
    expect(data.datePosted).toMatch(/^2026-09-24/);
    // The page's own CSP forbids script execution entirely.
    await expect(page.locator('script:not([type="application/ld+json"])')).toHaveCount(0);
    await expect(page.locator('meta[http-equiv="Content-Security-Policy"]')).toHaveAttribute('content', /default-src 'none'/);
  });

  test('OPEN IN JOB BOARD lands on the board with that job selected', async ({ page }) => {
    await page.goto(`/job/${FIXTURE.first}/`);

    await page.getByRole('link', { name: 'OPEN IN JOB BOARD' }).click();

    await expect(jobList(page)).toBeVisible();
    await expectSelected(page, FIXTURE.first);
  });
});

test.describe('security policy and analytics', () => {
  test('the app ships a CSP meta and loads without violations', async ({ page }) => {
    await openBoard(page);

    const csp = page.locator('meta[http-equiv="Content-Security-Policy"]');
    await expect(csp).toHaveAttribute('content', /script-src 'self' https:\/\/gc\.zgo\.at/);
    await expect(csp).toHaveAttribute('content', /object-src 'none'/);
    // Violations are collected by the shared fixture and fail the test on teardown.
  });

  test('GoatCounter loads ~3 s after load and is intercepted, never sent', async ({ page, externalCalls }) => {
    await openBoard(page);

    await expect.poll(() => externalCalls.some((u) => u.startsWith('https://gc.zgo.at/')), { timeout: 10_000 }).toBe(true);
    await expect(page.locator('script[data-goatcounter]')).toHaveCount(1);
    await expect(jobList(page)).toBeVisible();
  });
});
