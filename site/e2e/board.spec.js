// Desktop hiring board: list, search, facet filters, company filter, sorting.
import { test, expect } from './support/test.js';
import {
  FIXTURE, appliedIds, chip, detailTitle, expectParams, expectResults, expectSelected, jobList, openBoard,
  searchBox, selectedOption,
} from './support/app.js';

test.describe('job list', () => {
  test('renders every fixture job in a virtualized listbox with the first row selected', async ({ page }) => {
    await openBoard(page);

    await expectResults(page, FIXTURE.total);
    await expect(jobList(page)).toHaveAttribute('aria-label', `Jobs, ${FIXTURE.total} results`);
    await expectSelected(page, FIXTURE.first);
    await expect(detailTitle(page)).toHaveText(FIXTURE.firstTitle);
    const options = jobList(page).getByRole('option');
    await expect(options.first()).toHaveAttribute('aria-setsize', String(FIXTURE.total));
    await expect(options.first()).toHaveAttribute('aria-posinset', '1');
    // The prerendered crawlable list is replaced by the app on mount.
    await expect(page.locator('.ng-static')).toHaveCount(0);
  });

  test('clicking a row selects it and keeps focus on the listbox', async ({ page }) => {
    await openBoard(page);

    await jobList(page).locator(`[data-job-id="${FIXTURE.third}"]`).click();

    await expectSelected(page, FIXTURE.third);
    await expect(jobList(page)).toBeFocused();
    await expectParams(page, { job: FIXTURE.third });
  });

  test('the id-less job still renders and says no description is published', async ({ page }) => {
    await openBoard(page);
    await jobList(page).focus();

    await page.keyboard.press('End');

    await expectSelected(page, FIXTURE.last);
    await expect(detailTitle(page)).toHaveText('Software Engineer, New Grad');
    await expect(page.getByTestId('job-description')).toHaveText(/No description published/);
  });
});

test.describe('search', () => {
  test('matches company / role / location and mirrors the query into the URL', async ({ page }) => {
    await openBoard(page);

    await searchBox(page).fill('twilio');

    await expectResults(page, FIXTURE.twilioJobs);
    await expectParams(page, { q: 'twilio' });
    await expect(jobList(page).getByRole('option')).toHaveCount(FIXTURE.twilioJobs);
  });

  test('every whitespace-separated term must match, in any order', async ({ page }) => {
    await openBoard(page);

    await searchBox(page).fill('spain machine');

    await expectResults(page, 1);
    await expectSelected(page, FIXTURE.mlSpain);
  });

  test('no matches shows the empty state and an empty detail pane', async ({ page }) => {
    await openBoard(page);

    await searchBox(page).fill('zzz-no-such-job');

    await expectResults(page, 0);
    await expect(jobList(page)).toContainText('NO MATCHES');
    await expect(page.getByText('No job selected.')).toBeVisible();
  });
});

test.describe('facet filters', () => {
  test('ROLE chip narrows to the category and is reflected in aria-pressed + URL', async ({ page }) => {
    await openBoard(page);
    const ml = chip(page, 'ROLE', 'ml');

    await ml.click();

    await expect(ml).toHaveAttribute('aria-pressed', 'true');
    await expectResults(page, FIXTURE.mlJobs);
    await expectParams(page, { role: ['ML'] });

    await ml.click();
    await expect(ml).toHaveAttribute('aria-pressed', 'false');
    await expectResults(page, FIXTURE.total);
    await expectParams(page, { role: [] });
  });

  test('REMOTE chip filters on the derived remote/hybrid/onsite bucket', async ({ page }) => {
    await openBoard(page);

    await chip(page, 'REMOTE', 'remote').click();
    await expectResults(page, FIXTURE.remoteJobs);

    await chip(page, 'REMOTE', 'hybrid').click();
    await expectResults(page, FIXTURE.remoteJobs + 1);
    await expectParams(page, { remote: ['remote', 'hybrid'] });
  });

  test('COMPANY TIER chip filters on company_tier.tier', async ({ page }) => {
    await openBoard(page);

    await chip(page, 'COMPANY TIER', 'faang+').click();

    await expectResults(page, FIXTURE.faangJobs);
    await expect(selectedOption(page)).toHaveAccessibleName(/^Cisco,/);
    await expectParams(page, { tier: ['faang_plus'] });
  });

  test('VISA chips are a tri-state toggle', async ({ page }) => {
    await openBoard(page);
    const restricted = chip(page, 'VISA / CITIZENSHIP', 'restriction stated');
    const none = chip(page, 'VISA / CITIZENSHIP', 'no restriction stated');

    await restricted.click();
    await expectResults(page, FIXTURE.restrictedVisaJobs);
    await expectParams(page, { visa: 'restricted' });

    await none.click();
    await expect(restricted).toHaveAttribute('aria-pressed', 'false');
    await expectResults(page, FIXTURE.total - FIXTURE.restrictedVisaJobs);
    await expectParams(page, { visa: 'none' });

    await none.click();
    await expectResults(page, FIXTURE.total);
    await expectParams(page, { visa: null });
  });

  test('HIRING NOW company list filters to one company and keeps the other companies listed', async ({ page }) => {
    await openBoard(page);
    const hiringNow = page.getByRole('group', { name: /HIRING NOW/ });
    const anduril = hiringNow.getByRole('button', { name: `${FIXTURE.anduril.name}, ${FIXTURE.anduril.jobs} jobs` });
    const companiesBefore = await hiringNow.getByRole('button').count();

    await anduril.click();

    await expect(anduril).toHaveAttribute('aria-pressed', 'true');
    await expectResults(page, FIXTURE.anduril.jobs);
    await expectParams(page, { co: [FIXTURE.anduril.name] });
    await expect(hiringNow.getByRole('button')).toHaveCount(companiesBefore);
  });
});

test.describe('location facets', () => {
  test('a metro row narrows to that city and is reflected in the URL', async ({ page }) => {
    await openBoard(page);
    const lexington = page.getByRole('group', { name: 'LOCATION · metros' }).getByRole('button', { name: 'Lexington, MA, 2 jobs' });

    await lexington.click();

    await expect(lexington).toHaveAttribute('aria-pressed', 'true');
    await expectResults(page, 2);
    await expectParams(page, { metro: ['Lexington, MA'] });
    // The list is counted without the metro facet, so other metros stay clickable.
    await expect(page.getByRole('group', { name: 'LOCATION · metros' }).getByRole('button', { name: 'Kitsap, WA, 2 jobs' })).toBeVisible();
  });

  test('COUNTRY chips narrow to Canada or India', async ({ page }) => {
    await openBoard(page);

    await chip(page, 'COUNTRY', 'canada').click();
    await expectResults(page, 1);
    await expectParams(page, { country: ['CA'] });

    await chip(page, 'COUNTRY', 'canada').click();
    await chip(page, 'COUNTRY', 'india').click();
    await expectResults(page, 2);
  });
});

test.describe('WIDEN SCOPE (near misses)', () => {
  test('near misses are hidden by default and appear only for the toggled reasons', async ({ page }) => {
    await openBoard(page);
    await expectResults(page, FIXTURE.total);
    const interns = chip(page, 'WIDEN SCOPE', 'internships & co-ops');

    await interns.click();

    // The intern (1 reason) appears; the co-op abroad (2 reasons) needs both toggles.
    await expectResults(page, FIXTURE.total + 1, FIXTURE.total + 3);
    await expectParams(page, { include: ['intern_or_coop'] });
    await expect(page.getByRole('group', { name: 'WIDEN SCOPE' }).getByRole('button', { name: 'internships & co-ops (2)' })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[role="option"][data-job-id="job_e001ffffffffffffffff"]')).toContainText('intern');

    await chip(page, 'WIDEN SCOPE', 'outside US / CA / IN (1)').click();
    await expectResults(page, FIXTURE.total + 2, FIXTURE.total + 3);

    await page.keyboard.press('Escape');
    await expectResults(page, FIXTURE.total);
  });
});

test.describe('applied tracking and alerts', () => {
  test('the APPLIED button and the a key track the job in localStorage and mark the row', async ({ page }) => {
    await openBoard(page);

    await page.getByRole('button', { name: 'Mark as applied' }).click();

    await expect(page.getByRole('button', { name: 'Applied — unmark' })).toHaveAttribute('aria-pressed', 'true');
    await expect.poll(() => appliedIds(page)).toEqual([FIXTURE.first]);
    await expect(page.locator(`[role="option"][data-job-id="${FIXTURE.first}"]`)).toHaveAttribute('data-applied', 'true');

    await jobList(page).focus();
    await page.keyboard.press('a');
    await expect.poll(() => appliedIds(page)).toEqual([]);
  });

  test('the status bar RSS link follows the active filter', async ({ page }) => {
    await openBoard(page);
    const link = page.getByTestId('status-feed-link');
    // The generic feed lives in the footer; the status bar only shows a filter-specific slice.
    await expect(link).toHaveCount(0);

    await chip(page, 'ROLE', 'ml').click();
    await expect(link).toHaveAttribute('href', './feeds/data-ml.xml');

    await chip(page, 'ROLE', 'ml').click();
    await chip(page, 'REMOTE', 'remote').click();
    await expect(link).toHaveAttribute('href', './feeds/remote.xml');
  });
});

test.describe('sorting', () => {
  test('CO header sorts A→Z, a second click flips to Z→A', async ({ page }) => {
    await openBoard(page);
    const co = page.getByRole('button', { name: /^CO, / });

    await co.click();
    await expect(co).toHaveAccessibleName(/^CO, ascending/);
    await expect(jobList(page).getByRole('option').first()).toHaveAccessibleName(/^Affirm,/);
    await expectParams(page, { sort: 'co-asc' });

    await co.click();
    await expect(co).toHaveAccessibleName(/^CO, descending/);
    await expect(jobList(page).getByRole('option').first()).toHaveAccessibleName(/^xAI,/);
    await expectParams(page, { sort: 'co-desc' });
  });

  test('COMP header puts the highest posted salary first and unknown pay last', async ({ page }) => {
    await openBoard(page);

    await page.getByRole('button', { name: /^COMP, / }).click();

    const options = jobList(page).getByRole('option');
    await expect(options.nth(0)).toHaveAccessibleName(/^xAI,.*\$100–258k/);
    await expect(options.nth(1)).toHaveAccessibleName(/^Cisco,/);
    await expect(options.nth(2)).toHaveAccessibleName(/^Pilkington,/);
    await expect(page.getByRole('button', { name: /^POSTED, not sorted/ })).toBeVisible();
  });
});
