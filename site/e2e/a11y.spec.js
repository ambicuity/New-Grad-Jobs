// axe WCAG 2.2 AA scans of the desktop views and a per-job static page.
import { test, expect } from './support/test.js';
import { expectNoSeriousA11yViolations } from './support/axe.js';
import { FIXTURE, helpDialog, jobList, openBoard, tab } from './support/app.js';

test.describe('axe (WCAG 2.2 AA)', () => {
  test('hiring tab', async ({ page }, testInfo) => {
    await openBoard(page);
    await expect(page.getByTestId('job-description')).toContainText(FIXTURE.firstDescriptionStart);

    await expectNoSeriousA11yViolations(page, testInfo);
  });

  test('help dialog open', async ({ page }, testInfo) => {
    await openBoard(page);
    await jobList(page).focus();
    await page.keyboard.press('F1');
    await expect(helpDialog(page)).toBeVisible();

    await expectNoSeriousA11yViolations(page, testInfo);
  });

  test('contributors tab', async ({ page }, testInfo) => {
    await page.goto('/?tab=contributors');
    await expect(tab(page, 'CONTRIBUTORS')).toContainText(`${FIXTURE.contributors} devs`);
    await expect(page.getByRole('tabpanel')).toContainText('@ambicuity');

    await expectNoSeriousA11yViolations(page, testInfo);
  });

  test('per-job static page', async ({ page }, testInfo) => {
    await page.goto(`/job/${FIXTURE.first}/`);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    await expectNoSeriousA11yViolations(page, testInfo);
  });

  test('landing page and hub', async ({ page }, testInfo) => {
    await page.goto('/jobs/software-engineering/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expectNoSeriousA11yViolations(page, testInfo);

    await page.goto('/jobs/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expectNoSeriousA11yViolations(page, testInfo);
  });
});
