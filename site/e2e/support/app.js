// Locators and small actions shared by the specs. Facts about the fixture
// dataset (site/test/fixtures/jobs-index.json) live in FIXTURE so a change to
// the fixtures is a one-place edit here.

import { expect } from './test.js';

export const FIXTURE = {
  total: 20,
  // Default sort is POSTED ▼; ties break on job id, the id-less job sorts last.
  first: 'job_a000ffffffffffffffff',
  second: 'job_a900eeeeeeeeeeeeeeee',
  third: 'job_a901dddddddddddddddd',
  last: 'sparse-job',
  firstUrl: 'https://jobs.lever.co/palantir/a2e9ab0f-4dd1-4744-92b9-edc7ae393c58',
  firstTitle: 'Forward Deployed Software Engineer - US Government',
  firstDescriptionStart: 'A World-Changing Company',
  twilioJobs: 5,
  mlJobs: 3,
  remoteJobs: 7,
  faangJobs: 1,
  restrictedVisaJobs: 3,
  anduril: { name: 'Anduril Industries', jobs: 3 },
  mlSpain: 'job_a013ffffffffffffffff',
  contributors: 3,
};

export const SAVED_KEY = 'ngj:saved-jobs:v1';

export const jobList = (page) => page.getByRole('listbox', { name: /^Jobs,/ });
export const searchBox = (page) => page.getByRole('textbox', { name: 'Search jobs' });
export const resultCount = (page) => page.locator('#job-result-count');
export const detailTitle = (page) => page.locator('#job-detail-title');
export const selectedOption = (page) => page.locator('[role="option"][aria-selected="true"]');
export const helpDialog = (page) => page.getByRole('dialog', { name: 'KEYBOARD SHORTCUTS' });
export const tab = (page, name) => page.getByRole('tab', { name: new RegExp(`^${name}`) });
export const chip = (page, group, label) => page
  .getByRole('group', { name: group })
  .getByRole('button', { name: label, exact: true });

/** Open the board (optionally with a query string) and wait for React to mount the list. */
export async function openBoard(page, query = '') {
  await page.goto(`/${query}`);
  await expect(jobList(page)).toBeVisible();
}

export async function expectResults(page, n, total = FIXTURE.total) {
  await expect(resultCount(page)).toHaveText(`${n} / ${total} results`);
}

export async function expectSelected(page, jobId) {
  await expect(selectedOption(page)).toHaveAttribute('data-job-id', jobId);
  const optionId = await selectedOption(page).getAttribute('id');
  await expect(jobList(page)).toHaveAttribute('aria-activedescendant', optionId);
}

/**
 * URL writes are debounced (replaceState after 150 ms), so poll. `expected`
 * maps param → value (string, array for repeated params, null for absent).
 */
export async function expectParams(page, expected) {
  const read = () => {
    const params = new URL(page.url()).searchParams;
    return Object.fromEntries(Object.entries(expected).map(([k, v]) => {
      const all = params.getAll(k);
      if (Array.isArray(v)) return [k, all];
      return [k, all.length ? all[0] : null];
    }));
  };
  await expect.poll(read).toEqual(expected);
}

/** The query string exactly (e.g. '' for the default view), polled. */
export async function expectSearch(page, search) {
  await expect.poll(() => new URL(page.url()).search).toBe(search);
}

export async function savedIds(page) {
  return page.evaluate((key) => JSON.parse(window.localStorage.getItem(key) || '[]'), SAVED_KEY);
}
