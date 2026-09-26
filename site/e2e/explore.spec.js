// EXPLORE tab: the whole corpus, laid out like HIRING, filtered by the viewer's own words and facets.
import { test, expect } from './support/test.js';
import { expectNoSeriousA11yViolations } from './support/axe.js';
import { chip, expectParams, tab } from './support/app.js';

const list = (page) => page.getByRole('listbox', { name: /^All postings/ });
const rows = (page) => list(page).getByRole('option');
const count = (page) => page.locator('#explore-result-count');
const detail = (page) => page.getByTestId('explore-detail');

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
    await expect(rows(page).filter({ hasText: 'Trustworthy AI Lead' })).toHaveCount(0);

    const exclude = page.getByLabel('EXCLUDE · none of', { exact: true });
    await exclude.fill('senior');
    await exclude.press('Enter');
    await expect(count(page)).toContainText('1 / 10 postings');
    await expect(rows(page).first()).toContainText('Rust Engineer, Mission Autonomy');
    // The detail pane explains the match.
    await expect(detail(page)).toContainText('Rust Engineer, Mission Autonomy');
    await expect(detail(page)).toContainText('Matched include words');
    await expect(detail(page).locator('text=rust').first()).toBeVisible();

    await page.getByRole('button', { name: 'remove rust' }).click();
    await expect(count(page)).toContainText('9 / 10 postings');

    await page.getByRole('group', { name: 'TIER' }).getByRole('button', { name: /^curated \(/ }).click();
    await expect(count(page)).toContainText('2 / 10 postings');
    await expectParams(page, { xt: ['curated'], xe: ['senior'] });

    await page.getByRole('button', { name: 'clear all', exact: true }).click();
    await page.getByLabel('Search all postings').fill('anduril');
    await expect(count(page)).toContainText('2 / 10 postings');
  });

  test('signal chips, role / source / country facets and keyboard selection work like the board', async ({ page }) => {
    await page.goto('/?tab=explore');
    await expect(count(page)).toContainText('10 / 10');

    await chip(page, 'SIGNALS · exclude', 'senior').click();
    await expect(page.getByRole('list', { name: 'EXCLUDE · none of words' })).toContainText('senior');
    await expect(count(page)).toContainText('9 / 10');
    await expectParams(page, { xe: ['senior', 'sr', 'sr.'] });

    await page.getByRole('group', { name: 'ROLE' }).getByRole('button', { name: /^swe \(/ }).click();
    await expect(count(page)).toContainText('7 / 10');
    await expectParams(page, { xr: ['software_engineering'] });

    await page.getByRole('group', { name: 'SOURCE' }).getByRole('button', { name: /^Lever \(/ }).click();
    await expect(count(page)).toContainText('2 / 10');
    await page.getByRole('group', { name: 'SOURCE' }).getByRole('button', { name: /^Lever \(/ }).click();

    await page.getByRole('group', { name: 'COUNTRY' }).getByRole('button', { name: /^india \(/ }).click();
    await expect(count(page)).toContainText('1 / 10');
    await expectParams(page, { xc: ['IN'] });
    await page.getByRole('group', { name: 'COUNTRY' }).getByRole('button', { name: /^india \(/ }).click();
    // The list filters on a deferred copy of the facets; wait for it to settle before navigating it.
    await expect(count(page)).toContainText('7 / 10');
    await expect(list(page)).not.toHaveAttribute('aria-busy', 'true');

    // Keyboard: j moves the selection and the detail pane follows.
    await list(page).focus();
    const first = await rows(page).nth(0).getAttribute('aria-label');
    await page.keyboard.press('j');
    await expect(rows(page).nth(1)).toHaveAttribute('aria-selected', 'true');
    const second = await rows(page).nth(1).getAttribute('aria-label');
    expect(second).not.toBe(first);
    await expect(detail(page)).toContainText(second.split(', ')[1]);

    await expect(page.getByRole('button', { name: /^Export \d+ postings as CSV/ })).toBeEnabled();
  });

  test('presets apply a named signal set and the URL restores it', async ({ page }) => {
    await page.goto('/?tab=explore');
    await expect(count(page)).toContainText('10 / 10');

    await page.getByRole('button', { name: 'level II / L4 software' }).click();

    await expect(count(page)).toContainText('1 / 10 postings');
    await expect(rows(page).first()).toContainText('Software Engineer II, Payments');
    await expect(page.getByRole('button', { name: 'level II / L4 software' })).toHaveAttribute('aria-pressed', 'true');

    // The URL is written on a short debounce; wait for it before reloading.
    await expect(page).toHaveURL(/xi=engineer\+ii/);
    await page.reload();
    await expect(count(page)).toContainText('1 / 10 postings');
  });

  test('rail, list and detail pane fit a 1280px viewport with no horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/?tab=explore');
    await expect(count(page)).toContainText('10 / 10');
    await expect(detail(page)).toContainText('OPEN ON EMPLOYER SITE');
    const box = await detail(page).boundingBox();
    expect(box).not.toBeNull();
    expect(box.x + box.width).toBeLessThanOrEqual(1280);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBe(0);
    await expect(page.getByRole('button', { name: /^Export \d+ postings as CSV/ })).toBeInViewport();
  });

  test('is accessible', async ({ page }, testInfo) => {
    await page.goto('/?tab=explore&xi=rust');
    await expect(count(page)).toContainText('2 / 10');
    await expectNoSeriousA11yViolations(page, testInfo);
  });
});
