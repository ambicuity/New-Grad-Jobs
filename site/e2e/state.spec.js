// Persistence and navigation: saved jobs, URL view state, tabs, legacy links.
import { test, expect } from './support/test.js';
import {
  FIXTURE, SAVED_KEY, chip, detailTitle, expectParams, expectResults, expectSelected, jobList,
  openBoard, savedIds, searchBox, selectedOption, tab,
} from './support/app.js';
import { FIXTURE_STARS_DISPLAY } from './support/github-fixtures.js';

const savedToggle = (page) => page.getByRole('button', { name: /^SAVED: / });

test.describe('saved jobs', () => {
  test('S saves the selected job by job_id and it survives a reload', async ({ page }) => {
    await openBoard(page);
    await jobList(page).focus();

    await page.keyboard.press('s');

    await expect(page.getByRole('status')).toContainText('★ saved');
    await expect(page.getByRole('button', { name: /remove from saved jobs/ })).toHaveAttribute('aria-pressed', 'true');
    await expect(savedToggle(page)).toContainText('SAVED: 1');
    await expect.poll(() => savedIds(page)).toEqual([FIXTURE.first]);

    await page.reload();
    await expect(jobList(page)).toBeVisible();
    await expect(savedToggle(page)).toContainText('SAVED: 1');
    await expect(selectedOption(page)).toHaveAccessibleName(/, saved$/);
  });

  test('saved-only toggle shows just the saved jobs; S again unsaves', async ({ page }) => {
    await page.addInitScript(([key, ids]) => {
      if (!window.localStorage.getItem(key)) window.localStorage.setItem(key, JSON.stringify(ids));
    }, [SAVED_KEY, [FIXTURE.third, FIXTURE.mlSpain]]);
    await openBoard(page);

    await savedToggle(page).click();
    await expect(savedToggle(page)).toHaveAttribute('aria-pressed', 'true');
    await expectResults(page, 2);
    await expectParams(page, { saved: '1' });

    await jobList(page).focus();
    await page.keyboard.press('s');
    await expect(page.getByRole('status')).toContainText('removed from saved');
    await expect.poll(() => savedIds(page)).toEqual([FIXTURE.mlSpain]);
    await expectResults(page, 1);
  });

  test('saved-only with nothing saved just explains why', async ({ page }) => {
    await openBoard(page);

    await savedToggle(page).click();

    await expect(page.getByRole('status')).toContainText('no saved jobs yet');
    await expect(savedToggle(page)).toHaveAttribute('aria-pressed', 'false');
    await expectResults(page, FIXTURE.total);
  });
});

test.describe('URL state', () => {
  test('a shared link restores search, filters and the selected job — also after reload', async ({ page }) => {
    await openBoard(page, `?q=twilio&role=ML&job=${FIXTURE.mlSpain}`);

    const check = async () => {
      await expect(searchBox(page)).toHaveValue('twilio');
      await expect(chip(page, 'ROLE', 'ml')).toHaveAttribute('aria-pressed', 'true');
      await expectResults(page, FIXTURE.mlJobs);
      await expectSelected(page, FIXTURE.mlSpain);
      await expect(page.getByTestId('job-detail')).toContainText('Remote - Spain');
    };
    await check();
    await page.reload();
    await expect(jobList(page)).toBeVisible();
    await check();
  });

  test('unknown or malformed params are ignored', async ({ page }) => {
    await openBoard(page, '?role=NOPE&tier=x&sort=evil-asc&tab=admin&visa=maybe');

    await expectResults(page, FIXTURE.total);
    await expect(tab(page, 'HIRING')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('button', { name: /^POSTED, descending/ })).toBeVisible();
  });

  test('switching tabs pushes history: Back returns to the board with its state', async ({ page }) => {
    await openBoard(page);
    await searchBox(page).fill('anduril');
    await expectParams(page, { q: 'anduril' });

    await tab(page, 'CONTRIBUTORS').click();
    await expect(tab(page, 'CONTRIBUTORS')).toHaveAttribute('aria-selected', 'true');
    await expectParams(page, { tab: 'contributors', q: 'anduril' });

    await page.goBack();
    await expect(tab(page, 'HIRING')).toHaveAttribute('aria-selected', 'true');
    await expect(searchBox(page)).toHaveValue('anduril');
    await expectResults(page, FIXTURE.anduril.jobs);

    await page.goForward();
    await expect(tab(page, 'CONTRIBUTORS')).toHaveAttribute('aria-selected', 'true');
  });

  test('arrow keys move between the view tabs', async ({ page }) => {
    await openBoard(page);
    await tab(page, 'HIRING').focus();

    await page.keyboard.press('ArrowRight');

    await expect(tab(page, 'CONTRIBUTORS')).toBeFocused();
    await expect(tab(page, 'CONTRIBUTORS')).toHaveAttribute('aria-selected', 'true');
  });
});

test.describe('contributors tab', () => {
  test('?tab=contributors opens the contributors view with (mocked) GitHub stats', async ({ page, externalCalls }) => {
    await page.goto('/?tab=contributors');

    await expect(tab(page, 'CONTRIBUTORS')).toHaveAttribute('aria-selected', 'true');
    await expect(tab(page, 'CONTRIBUTORS')).toContainText(`${FIXTURE.contributors} devs`);
    await expect(page.getByRole('tabpanel')).toContainText('@ambicuity');
    // STARS comes from the mocked /repos call (4242 → fmtK → "4.2k").
    await expect(page.getByRole('tabpanel')).toContainText(FIXTURE_STARS_DISPLAY);
    expect(externalCalls.some((u) => u.startsWith('https://api.github.com/repos/ambicuity/New-Grad-Jobs'))).toBe(true);
  });

  test('legacy #contributors links open the tab and are folded into ?tab=', async ({ page }) => {
    await page.goto('/#contributors');

    await expect(tab(page, 'CONTRIBUTORS')).toHaveAttribute('aria-selected', 'true');
    await expect.poll(() => { const u = new URL(page.url()); return `${u.search}${u.hash}`; }).toBe('?tab=contributors');
  });

  test('contributors.html redirects to the contributors tab', async ({ page }) => {
    await page.goto('/contributors.html');

    await expect(page).toHaveURL(/\?tab=contributors/);
    await expect(tab(page, 'CONTRIBUTORS')).toHaveAttribute('aria-selected', 'true');
  });
});

test.describe('job description', () => {
  test('is lazy-loaded from its descriptions shard', async ({ page }) => {
    const shard = page.waitForResponse((r) => r.url().endsWith('/descriptions/a.json'));
    await openBoard(page);

    expect((await shard).status()).toBe(200);
    await expect(page.getByTestId('job-description')).toContainText(FIXTURE.firstDescriptionStart);
    await expect(page.getByRole('region', { name: 'Job description' })).toBeVisible();
  });

  test.describe('when the shard 404s', () => {
    test.use({ allowConsoleErrors: /404|description shard failed/ });

    test('shows "description unavailable" with a working RETRY', async ({ page }) => {
      let failing = true;
      await page.route('**/descriptions/a.json', (route) => (failing
        ? route.fulfill({ status: 404, body: 'not found' })
        : route.fallback()));
      await openBoard(page);

      const desc = page.getByTestId('job-description');
      await expect(desc).toHaveRole('alert');
      await expect(desc).toContainText('description unavailable');

      failing = false;
      await desc.getByRole('button', { name: /RETRY/ }).click();
      await expect(desc).toContainText(FIXTURE.firstDescriptionStart);
      await expect(detailTitle(page)).toHaveText(FIXTURE.firstTitle);
    });
  });
});

test.describe('when the job data cannot be loaded', () => {
  test.use({ allowConsoleErrors: /404|failed to load jobs\.json/ });

  test('shows the COULDN\'T LOAD JOBS panel instead of an empty board', async ({ page }) => {
    await page.route(/\/jobs(-index)?\.json(\?|$)/, (route) => route.fulfill({ status: 404, body: 'gone' }));
    await page.goto('/');

    const alert = page.getByRole('alert').filter({ hasText: 'COULDN\'T LOAD JOBS' });
    await expect(alert).toBeVisible();
    await expect(alert).toContainText('jobs.json: HTTP 404');
    await expect(alert.getByRole('button', { name: /RETRY/ })).toBeVisible();
    await expect(tab(page, 'HIRING')).toContainText('offline');
    await expect(jobList(page)).toHaveCount(0);
  });
});
