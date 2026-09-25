// EXPLORE tab: the whole corpus, filtered by the viewer's own words.
import { test, expect } from './support/test.js';
import { expectNoSeriousA11yViolations } from './support/axe.js';
import { expectParams, tab } from './support/app.js';

const rows = (page) => page.getByRole('list', { name: /^All postings/ }).getByRole('listitem');
const count = (page) => page.locator('#explore-result-count');

test.describe('explore', () => {
  test('loads the corpus on demand and filters with include / exclude words, tiers and the query', async ({ page }) => {
    await page.goto('/?tab=explore');
    await expect(tab(page, 'EXPLORE')).toHaveAttribute('aria-selected', 'true');
    await expect(count(page)).toContainText('10 / 10 postings');
    await expect(rows(page)).toHaveCount(10);

    const include = page.getByLabel('INCLUDE · any of', { exact: true });
    await include.fill('rust');
    await include.press('Enter');
    await expect(count(page)).toContainText('2 / 10 postings');
    await expectParams(page, { xi: ['rust'] });
    // "Trustworthy AI Lead" must not match "rust": whole words only, like the scraper.
    await expect(page.getByRole('link', { name: 'Trustworthy AI Lead' })).toHaveCount(0);

    const exclude = page.getByLabel('EXCLUDE · none of', { exact: true });
    await exclude.fill('senior');
    await exclude.press('Enter');
    await expect(count(page)).toContainText('1 / 10 postings');
    await expect(page.getByRole('link', { name: 'Rust Engineer, Mission Autonomy' })).toBeVisible();

    await page.getByRole('button', { name: 'remove rust' }).click();
    await expect(count(page)).toContainText('9 / 10 postings');

    await page.getByRole('group', { name: 'TIER' }).getByRole('button', { name: 'curated (2)' }).click();
    await expect(count(page)).toContainText('2 / 10 postings');
    await expectParams(page, { xt: ['curated'], xe: ['senior'] });

    await page.getByRole('button', { name: 'clear', exact: true }).click();
    await page.getByLabel('Search all postings').fill('anduril');
    await expect(count(page)).toContainText('2 / 10 postings');
  });

  test('presets apply a named signal set and the URL restores it', async ({ page }) => {
    await page.goto('/?tab=explore');
    await expect(count(page)).toContainText('10 / 10');

    await page.getByRole('button', { name: 'level II / L4 software' }).click();

    await expect(count(page)).toContainText('1 / 10 postings');
    await expect(page.getByRole('link', { name: 'Software Engineer II, Payments' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'level II / L4 software' })).toHaveAttribute('aria-pressed', 'true');

    // The URL is written on a short debounce; wait for it before reloading.
    await expect(page).toHaveURL(/xi=engineer\+ii/);
    await page.reload();
    await expect(count(page)).toContainText('1 / 10 postings');
  });

  test('is accessible', async ({ page }, testInfo) => {
    await page.goto('/?tab=explore&xi=rust');
    await expect(count(page)).toContainText('2 / 10');
    await expectNoSeriousA11yViolations(page, testInfo);
  });
});
