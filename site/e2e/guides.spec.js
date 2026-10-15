// The /guides/ layout on desktop: complete without JavaScript, enhanced with
// search, views, formats and read/saved marks by the same-origin guides.js.
import { test, expect } from './support/test.js';

const cards = (page) => page.locator('.card:not([hidden])');

test.describe('guides index', () => {
  test('search, format filter and empty state, counted from the page', async ({ page }) => {
    await page.goto('/guides/');
    const total = await page.locator('.card').count();
    await expect(page.locator('[data-guides-count]')).toHaveText(`Showing ${total} of ${total} guides`);
    await page.getByLabel('Search guides').fill('resume');
    await expect(cards(page).first()).toBeVisible();
    const shown = await cards(page).count();
    expect(shown).toBeLessThan(total);
    for (const text of await cards(page).evaluateAll((els) => els.map((el) => el.dataset.text))) {
      expect(text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')).toContain('resume');
    }
    await page.getByLabel('Search guides').fill('zzzz-nothing');
    await expect(page.getByText('No guides match these filters.')).toBeVisible();
    await page.getByRole('button', { name: 'Clear search and filters' }).click();
    await expect(cards(page)).toHaveCount(total);
    await page.getByLabel('Format').selectOption('script');
    const scripts = await cards(page).count();
    expect(scripts).toBeGreaterThan(0);
    expect(scripts).toBeLessThan(total);
    expect(await cards(page).locator('.tag', { hasText: 'SCRIPT' }).count()).toBe(scripts);
  });

  test('"/" focuses search and reading paths open one at a time', async ({ page }) => {
    await page.goto('/guides/');
    await page.keyboard.press('/');
    await expect(page.getByLabel('Search guides')).toBeFocused();
    await page.keyboard.press('Escape');
    await page.locator('#path-have-offer summary').click();
    await expect(page.locator('#path-have-offer')).toHaveAttribute('open', '');
    await expect(page.locator('#path-have-offer li').first()).toContainText('Evaluating');
    await page.locator('#path-international summary').click();
    await expect(page.locator('#path-international')).toHaveAttribute('open', '');
    await expect(page.locator('#path-have-offer')).not.toHaveAttribute('open', '');
  });

  test('saved and read marks persist and flow between a guide and the index', async ({ page }) => {
    await page.goto('/guides/negotiation/');
    await page.getByRole('button', { name: 'Mark as read' }).click();
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Mark as read' })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByRole('button', { name: 'Save', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await page.goto('/guides/');
    await expect(page.locator('[data-count="saved"]')).toHaveText('1');
    await expect(page.locator('[data-count="read"]')).toHaveText('1');
    await expect(page.locator('[data-guide="negotiation"]')).toHaveClass(/is-read/);
    await page.getByRole('button', { name: /Saved/ }).click();
    await expect(cards(page)).toHaveCount(1);
    await page.getByRole('button', { name: 'Save Negotiating a new grad offer' }).click();
    await expect(cards(page)).toHaveCount(0);
    await page.reload();
    await expect(page.locator('[data-count="saved"]')).toHaveText('0');
  });
});

test.describe('guide page', () => {
  test('brief, side contents with working anchors, and prev/next links', async ({ page }) => {
    await page.goto('/guides/negotiation/');
    await expect(page.getByLabel('30-second brief')).toContainText('Read this when');
    const side = page.getByRole('navigation', { name: 'On this page', exact: true });
    await expect(side).toBeVisible();
    await expect(page.locator('.toc-inline')).toBeHidden();
    const first = side.getByRole('link').first();
    const id = (await first.getAttribute('href')).slice(1);
    await first.click();
    await expect(page).toHaveURL(new RegExp(`#${id}$`));
    await expect(page.locator(`[id="${id}"]`)).toBeInViewport();
    await expect(page.locator('.pager a[rel="next"]')).toHaveAttribute('href', /^\.\.\/\.\.\/guides\/[a-z0-9-]+\/$/);
  });
});

test.describe('guides without JavaScript', () => {
  test.use({ javaScriptEnabled: false });

  test('every guide, path and section is still listed; enhancement controls stay hidden', async ({ page }) => {
    await page.goto('/guides/');
    await expect(page.locator('.card').first()).toBeVisible();
    await expect(page.locator('[data-guides-toolbar]')).toBeHidden();
    await expect(page.locator('.star').first()).toBeHidden();
    await page.locator('#path-no-interviews summary').click();
    await expect(page.locator('#path-no-interviews li').first()).toBeVisible();
    await page.goto('/guides/negotiation/');
    await expect(page.locator('[data-guide-tools]')).toBeHidden();
    await expect(page.getByLabel('30-second brief')).toBeVisible();
  });
});
