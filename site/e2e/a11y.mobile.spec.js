// axe WCAG 2.2 AA scans of the phone layout.
import { test, expect } from './support/test.js';
import { expectNoSeriousA11yViolations } from './support/axe.js';
import { FIXTURE } from './support/app.js';

test.describe('axe (WCAG 2.2 AA), 375px', () => {
  test('card list', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.getByTestId('job-list').getByRole('listitem').first()).toBeVisible();

    await expectNoSeriousA11yViolations(page, testInfo);
  });

  test('job detail dialog', async ({ page }, testInfo) => {
    await page.goto('/');
    await page.locator(`button[data-job-id="${FIXTURE.first}"]`).tap();
    const dialog = page.getByRole('dialog', { name: /^Palantir · / });
    await expect(dialog.getByTestId('job-description')).toContainText(FIXTURE.firstDescriptionStart);

    await expectNoSeriousA11yViolations(page, testInfo);
  });
});
