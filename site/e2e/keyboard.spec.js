// Desktop keyboard model: global shortcuts, Esc, the help dialog.
import { test, expect } from './support/test.js';
import {
  FIXTURE, chip, detailTitle, expectResults, expectSearch, expectSelected, helpDialog, jobList,
  openBoard, searchBox,
} from './support/app.js';

test.describe('shortcuts', () => {
  test('/ focuses the search box; Esc inside it only blurs', async ({ page }) => {
    await openBoard(page);
    await searchBox(page).fill('twilio');
    await jobList(page).focus();

    await page.keyboard.press('/');
    await expect(searchBox(page)).toBeFocused();

    await page.keyboard.press('Escape');
    await expect(searchBox(page)).not.toBeFocused();
    await expect(searchBox(page)).toHaveValue('twilio');
  });

  test('j / k and the arrow keys move the selection; Home / End jump', async ({ page }) => {
    await openBoard(page);
    await jobList(page).focus();

    await page.keyboard.press('j');
    await expectSelected(page, FIXTURE.second);
    await page.keyboard.press('ArrowDown');
    await expectSelected(page, FIXTURE.third);
    await page.keyboard.press('k');
    await expectSelected(page, FIXTURE.second);
    await page.keyboard.press('ArrowUp');
    await expectSelected(page, FIXTURE.first);
    // Clamped at the top.
    await page.keyboard.press('k');
    await expectSelected(page, FIXTURE.first);

    await page.keyboard.press('End');
    await expectSelected(page, FIXTURE.last);
    await page.keyboard.press('Home');
    await expectSelected(page, FIXTURE.first);
  });

  test('shortcuts stand aside while typing in the search box', async ({ page }) => {
    await openBoard(page);
    await searchBox(page).focus();

    await page.keyboard.type('jk');

    await expect(searchBox(page)).toHaveValue('jk');
    await expect(helpDialog(page)).toHaveCount(0);
  });

  test('Enter opens the selected job\'s application in a new tab (no navigation)', async ({ page }) => {
    await page.addInitScript(() => {
      window.__opened = [];
      window.open = (...args) => { window.__opened.push(args); return null; };
    });
    await openBoard(page);
    await jobList(page).focus();

    await page.keyboard.press('Enter');

    await expect.poll(() => page.evaluate(() => window.__opened)).toEqual([
      [FIXTURE.firstUrl, '_blank', 'noopener,noreferrer'],
    ]);
    await expect(page.getByRole('status')).toContainText('opening palantir');
    // Still on the board: Enter never navigates this tab.
    expect(new URL(page.url()).hostname).toBe('127.0.0.1');
    await expect(jobList(page)).toBeVisible();
  });

  test('the APPLY link targets the posting in a new tab with noopener', async ({ page }) => {
    await openBoard(page);

    const apply = page.getByRole('link', { name: /^APPLY ↗/ });

    await expect(apply).toHaveAttribute('href', FIXTURE.firstUrl);
    await expect(apply).toHaveAttribute('target', '_blank');
    await expect(apply).toHaveAttribute('rel', /noopener/);
    await expect(apply).toHaveAttribute('rel', /noreferrer/);
  });

  test('F2 cycles the sort key', async ({ page }) => {
    await openBoard(page);
    await jobList(page).focus();

    await page.keyboard.press('F2');
    await expect(page.getByRole('button', { name: /^COMP, descending/ })).toBeVisible();
    await page.keyboard.press('F2');
    await expect(page.getByRole('button', { name: /^CO, ascending/ })).toBeVisible();
    await page.keyboard.press('F2');
    await expect(page.getByRole('button', { name: /^POSTED, descending/ })).toBeVisible();
  });

  test('Esc clears the search and every filter in one go (URL back to the default view)', async ({ page }) => {
    await openBoard(page, '?q=engineer&remote=remote&tier=unicorn');
    await chip(page, 'ROLE', 'ml').click();
    await expectResults(page, 3);

    await jobList(page).focus();
    await page.keyboard.press('Escape');

    await expectResults(page, FIXTURE.total);
    await expect(searchBox(page)).toHaveValue('');
    await expect(chip(page, 'ROLE', 'ml')).toHaveAttribute('aria-pressed', 'false');
    await expect(chip(page, 'REMOTE', 'remote')).toHaveAttribute('aria-pressed', 'false');
    await expect(page.getByRole('status')).toContainText('filters cleared');
    await expectSearch(page, '');
  });
});

test.describe('help dialog', () => {
  test('F1 opens a modal help dialog with focus inside and a Tab trap', async ({ page }) => {
    await openBoard(page);
    await jobList(page).focus();

    await page.keyboard.press('F1');

    const dialog = helpDialog(page);
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('aria-modal', 'true');
    const close = dialog.getByRole('button', { name: /CLOSE/ });
    await expect(close).toBeFocused();
    for (const key of ['Tab', 'Tab', 'Shift+Tab']) {
      await page.keyboard.press(key);
      await expect(close).toBeFocused();
    }
    // Page shortcuts are off while the dialog is open.
    await page.keyboard.press('j');
    await expectSelected(page, FIXTURE.first);
  });

  test('? opens it too; Esc closes it, returns focus and does not clear filters', async ({ page }) => {
    await openBoard(page, '?q=twilio');
    await jobList(page).focus();

    await page.keyboard.press('?');
    await expect(helpDialog(page)).toBeVisible();
    await page.keyboard.press('Escape');

    await expect(helpDialog(page)).toHaveCount(0);
    await expect(jobList(page)).toBeFocused();
    await expect(searchBox(page)).toHaveValue('twilio');
  });

  test('CLOSE button and backdrop click dismiss it', async ({ page }) => {
    await openBoard(page);
    await jobList(page).focus();

    await page.keyboard.press('F1');
    await helpDialog(page).getByRole('button', { name: /CLOSE/ }).click();
    await expect(helpDialog(page)).toHaveCount(0);

    await jobList(page).focus();
    await page.keyboard.press('F1');
    await page.mouse.click(5, 450);
    await expect(helpDialog(page)).toHaveCount(0);
    await expect(detailTitle(page)).toHaveText(FIXTURE.firstTitle);
  });
});
