// The /guides/ layout at 375px: no sideways scrolling, search reachable on the
// first screen, contents folded inline instead of the side column.
import { test, expect } from './support/test.js';

const noOverflow = async (page) => {
  const w = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: window.innerWidth }));
  expect(w.content).toBeLessThanOrEqual(w.viewport);
};

test.describe('guides at 375px', () => {
  test('index fits the screen with search on the first screen', async ({ page }) => {
    await page.goto('/guides/');
    await noOverflow(page);
    const search = page.getByLabel('Search guides');
    await expect(search).toBeInViewport();
    await search.fill('offer');
    await expect(page.locator('.card:not([hidden])').first()).toBeVisible();
    await page.locator('.card:not([hidden]) .star').first().tap();
    await expect(page.locator('[data-count="saved"]')).toHaveText('1');
  });

  for (const slug of ['negotiation', 'opt-and-stem-opt', 'resume-evidence-test', 'ai-assisted-interviews']) {
    test(`${slug} fits the screen with inline contents`, async ({ page }) => {
      await page.goto(`/guides/${slug}/`);
      await noOverflow(page);
      await expect(page.locator('.toc-side')).toBeHidden();
      const inline = page.locator('.toc-inline');
      await expect(inline).toBeVisible();
      await inline.locator('summary').tap();
      await expect(inline.getByRole('link').first()).toBeVisible();
    });
  }
});
