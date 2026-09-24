// Phone layout (375px, touch): card list → full-screen detail dialog.
import { test, expect } from './support/test.js';
import { FIXTURE, SAVED_KEY, expectParams, expectResults, savedIds } from './support/app.js';

const cards = (page) => page.getByTestId('job-list').getByRole('listitem');
const openButton = (page, jobId) => page.locator(`button[data-job-id="${jobId}"]`);
const detailDialog = (page) => page.getByRole('dialog', { name: /^Palantir · / });

async function openMobileBoard(page, query = '') {
  await page.goto(`/${query}`);
  await expect(cards(page).first()).toBeVisible();
}

test('renders a single-column card list without horizontal scroll', async ({ page }) => {
  await openMobileBoard(page);

  await expect(page.getByRole('listbox')).toHaveCount(0);
  await expect(page.getByTestId('job-list').getByRole('list')).toBeVisible();
  await expectResults(page, FIXTURE.total);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test('tapping a card opens the detail dialog; browser Back closes it', async ({ page }) => {
  await openMobileBoard(page);

  await openButton(page, FIXTURE.first).tap();

  const dialog = detailDialog(page);
  await expect(dialog).toBeVisible();
  await expect(dialog).toHaveAttribute('aria-modal', 'true');
  await expect(dialog.getByRole('button', { name: 'Back to job list' })).toBeFocused();
  await expect(dialog.getByRole('heading', { level: 2 })).toHaveText(FIXTURE.firstTitle);
  await expect(dialog.getByTestId('job-description')).toContainText(FIXTURE.firstDescriptionStart);
  await expectParams(page, { job: FIXTURE.first });

  await page.goBack();

  await expect(dialog).toHaveCount(0);
  await expectParams(page, { job: null });
  await expect(openButton(page, FIXTURE.first)).toBeVisible();
});

test('the ‹ BACK button closes the detail and pops its history entry', async ({ page }) => {
  await openMobileBoard(page);
  await openButton(page, FIXTURE.first).tap();
  const historyWithDetail = await page.evaluate(() => window.history.length);

  await detailDialog(page).getByRole('button', { name: 'Back to job list' }).tap();

  await expect(detailDialog(page)).toHaveCount(0);
  await expectParams(page, { job: null });
  // Closing went back rather than stacking another entry.
  expect(await page.evaluate(() => window.history.length)).toBe(historyWithDetail);
  await expect(openButton(page, FIXTURE.first)).toBeFocused();
});

test('a deep link to ?job= opens the detail directly and Esc closes it', async ({ page }) => {
  await page.goto(`/?job=${FIXTURE.first}`);

  await expect(detailDialog(page)).toBeVisible();
  await page.keyboard.press('Escape');

  await expect(detailDialog(page)).toHaveCount(0);
  await expectParams(page, { job: null });
});

test('the FILTERS drawer expands and reports active filters', async ({ page }) => {
  await openMobileBoard(page);
  const drawer = page.getByRole('button', { name: /FILTERS/ });
  await expect(drawer).toHaveAttribute('aria-expanded', 'false');

  await drawer.tap();
  await expect(drawer).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('group', { name: 'REMOTE' }).getByRole('button', { name: 'remote', exact: true }).tap();

  await expectResults(page, FIXTURE.remoteJobs);
  await expect(drawer).toContainText('1 active');
});

test('the card star saves the job to localStorage', async ({ page }) => {
  await openMobileBoard(page);

  const star = page.getByRole('button', { name: 'Save Palantir job' }).first();
  await star.tap();

  await expect(page.getByRole('button', { name: 'Remove Palantir job' }).first()).toHaveAttribute('aria-pressed', 'true');
  await expect.poll(() => savedIds(page)).toEqual([FIXTURE.first]);
  expect(SAVED_KEY).toBe('ngj:saved-jobs:v1');
});
