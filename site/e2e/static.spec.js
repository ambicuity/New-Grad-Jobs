// Build output outside the SPA: per-job static pages, CSP, hermetic analytics.
import { test, expect } from './support/test.js';
import { FIXTURE, expectResults, expectSelected, jobList, openBoard } from './support/app.js';

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

test.describe('landing pages', () => {
  test('category page lists real jobs with ItemList JSON-LD and no scripts', async ({ page }) => {
    const res = await page.goto('/jobs/software-engineering/');
    expect(res.status()).toBe(200);

    await expect(page.getByRole('heading', { level: 1 })).toHaveText('New grad Software Engineering jobs');
    const blocks = page.locator('script[type="application/ld+json"]');
    await expect(blocks).toHaveCount(1);
    const data = JSON.parse(await blocks.textContent());
    expect(data['@type']).toBe('ItemList');
    expect(data.numberOfItems).toBeGreaterThan(0);
    expect(data.itemListElement[0].url).toMatch(/\/job\/job_[0-9a-f]+\/$/);
    await expect(page.locator('script:not([type="application/ld+json"])')).toHaveCount(0);
    await expect(page.locator('meta[http-equiv="Content-Security-Policy"]')).toHaveAttribute('content', /default-src 'none'/);
    // The first listed job links to its own static page.
    await page.getByRole('list').getByRole('link').first().click();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(FIXTURE.firstTitle);
  });

  test('OPEN IN JOB BOARD applies the matching filter on the board', async ({ page }) => {
    await page.goto('/jobs/remote/');

    await page.getByRole('link', { name: 'OPEN IN JOB BOARD' }).click();

    await expect(jobList(page)).toBeVisible();
    await expect(page).toHaveURL(/[?&]remote=remote/);
    await expectResults(page, FIXTURE.remoteJobs);
  });

  test('hub links every landing page with a live count', async ({ page }) => {
    await page.goto('/jobs/');

    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Browse new grad jobs');
    const swe = page.getByRole('link', { name: 'Software Engineering', exact: true });
    await expect(swe).toHaveAttribute('href', '../jobs/software-engineering/');
    await expect(page.getByRole('link', { name: 'Remote', exact: true })).toBeVisible();
    await expect(page.locator('main')).toContainText(`${FIXTURE.remoteJobs} open`);
  });
});

test.describe('guides and about', () => {
  test('a guide renders as an article with Article JSON-LD and no scripts', async ({ page }) => {
    const res = await page.goto('/guides/reading-a-new-grad-posting/');
    expect(res.status()).toBe(200);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Reading a new grad job posting');
    const blocks = page.locator('script[type="application/ld+json"]');
    await expect(blocks).toHaveCount(1);
    expect(JSON.parse(await blocks.textContent())['@type']).toBe('Article');
    await expect(page.locator('script:not([type="application/ld+json"])')).toHaveCount(0);
  });

  test('the about page reports this run from health.json', async ({ page }) => {
    await page.goto('/about/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('How this board works');
    await expect(page.locator('main')).toContainText(`open roles`);
    await expect(page.locator('main')).toContainText(String(FIXTURE.total - 1));
  });
});

test.describe('data compression', () => {
  test('the board loads its index as Brotli when the browser decodes it, else as the gzip json', async ({ page }) => {
    const urls = [];
    page.on('response', (r) => { if (/jobs-index\.json(\.br)?$/.test(r.url()) && r.status() === 200) urls.push(r.url()); });
    await openBoard(page);
    const br = urls.some((u) => u.endsWith('.br'));
    const json = urls.some((u) => u.endsWith('.json'));
    expect(br || json).toBe(true);
    if (br) expect(json).toBe(false); // no double download
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
