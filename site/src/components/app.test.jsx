// @vitest-environment jsdom
// Behaviour tests for the rendered views against the fixture dataset.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { normalizeJobsPayload } from '../lib/jobs.js';
import { SAVED_STORAGE_KEY } from '../lib/saved.js';
import { URL_WRITE_DELAY_MS } from '../hooks/useUrlViewState.js';
import { applyGhEnrichment, DEFAULT_REPO, mapContributor } from '../lib/contributors.js';
import { App } from './shell/App.jsx';

// The real module keeps one shard cache for the page's lifetime; give each
// test a fresh one so its fetch mock applies.
const shardCache = vi.hoisted(() => ({ reset: () => {} }));
vi.mock('../data/descriptions-source.js', async (importOriginal) => {
  const real = await importOriginal();
  let loader = real.createShardLoader();
  shardCache.reset = () => { loader = real.createShardLoader(); };
  return { ...real, loadDescriptionShard: (k) => loader(k) };
});

// Vitest runs from site/, and import.meta.url is not a file: URL under jsdom.
const fixture = (rel) => JSON.parse(readFileSync(resolve(process.cwd(), 'test/fixtures', rel), 'utf8'));
const rawJobs = fixture('jobs-index.json');
const jobsState = { ...normalizeJobsPayload(rawJobs), error: null };
const contributorsState = applyGhEnrichment(fixture('contributors.json').contributors.map(mapContributor), DEFAULT_REPO, null);
const shard = fixture('descriptions/a.json');

function mockMatchMedia(mobile) {
  window.matchMedia = vi.fn(() => ({ matches: mobile, addEventListener: () => {}, removeEventListener: () => {} }));
}

// jsdom has no layout. The virtualizer reads offsetHeight/offsetWidth: give the
// scroll viewport 800px and each measured mobile card 90px, so the fixture's
// 20 rows all fit in the rendered window.
const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
    configurable: true, get() { return this.hasAttribute('data-index') ? 90 : 800; },
  });
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, get() { return 800; } });
  Element.prototype.scrollTo = function scrollTo() {};
});
afterAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', originalOffsetHeight);
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', originalOffsetWidth);
});

// Node's own experimental localStorage global can shadow jsdom's; install a
// plain in-memory Storage so the tests control it.
function memoryStorage() {
  const data = new Map();
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => { data.set(k, String(v)); },
    removeItem: (k) => { data.delete(k); },
    clear: () => data.clear(),
  };
}

let shardResponse = () => Promise.resolve({ ok: true, json: () => Promise.resolve(shard) });
beforeEach(() => {
  window.history.replaceState(null, '', '/');
  shardCache.reset();
  Object.defineProperty(window, 'localStorage', { configurable: true, value: memoryStorage() });
  mockMatchMedia(false);
  shardResponse = () => Promise.resolve({ ok: true, json: () => Promise.resolve(shard) });
  globalThis.fetch = vi.fn((url) => {
    if (String(url).includes('descriptions/a.json')) return shardResponse();
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
  });
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const renderApp = (state = jobsState) => render(
  <App jobsState={state} contributorsPromise={Promise.resolve(contributorsState)} />,
);
const listbox = () => screen.getByRole('listbox');
const rows = () => [...document.querySelectorAll('[data-testid="job-list"] [data-job-id]')];
const selectedRow = () => document.querySelector('[data-testid="job-list"] [aria-selected="true"]');
const expectText = (el, text) => {
  if (text instanceof RegExp) expect(el.textContent).toMatch(text);
  else expect(el.textContent).toContain(text);
};
const key = (k, opts = {}, target = window) => act(() => { fireEvent.keyDown(target, { key: k, ...opts }); });
const params = () => new URLSearchParams(window.location.search);
// Let the debounced replaceState land.
const flushUrl = () => act(() => new Promise((r) => { setTimeout(r, URL_WRITE_DELAY_MS + 20); }));

describe('hiring view (desktop)', () => {
  it('renders every fixture job in a listbox and the tab counts', async () => {
    renderApp();
    expect(rows()).toHaveLength(20);
    expect(listbox().getAttribute('aria-label')).toMatch(/20 results/);
    expectText(screen.getByRole('tab', { name: /HIRING/ }), '20 open');
    await screen.findByText('3 devs');
  });

  it('has a main landmark, a page heading and skip links', () => {
    renderApp();
    expect(screen.getByRole('main')).toBeTruthy();
    expect(screen.getByRole('heading', { level: 1 }).textContent).toMatch(/New Grad Jobs/);
    const skip = screen.getByRole('link', { name: 'Skip to job list' });
    fireEvent.click(skip);
    expect(document.activeElement).toBe(listbox());
    fireEvent.click(screen.getByRole('link', { name: 'Skip to job search' }));
    expect(document.activeElement).toBe(screen.getByLabelText('Search jobs'));
    expect(window.location.hash).toBe('');
  });

  it('j/k move the selection (aria-activedescendant follows) and the detail lazy-loads', async () => {
    renderApp();
    const first = selectedRow().dataset.jobId;
    key('j');
    const second = selectedRow().dataset.jobId;
    expect(second).not.toBe(first);
    expect(listbox().getAttribute('aria-activedescendant')).toBe(selectedRow().id);
    key('k');
    expect(selectedRow().dataset.jobId).toBe(first);
    key('End');
    expect(selectedRow().dataset.jobId).toBe(rows()[rows().length - 1].dataset.jobId);
    key('Home');
    expect(selectedRow().dataset.jobId).toBe(first);
    const job = jobsState.jobs.find((j) => j.id === first);
    await vi.waitFor(() => expect(screen.getByTestId('job-description').textContent).toBe(shard[job.jobId].trim()));
  });

  it('shows "loading…" (never the previous job\'s text) while a description loads', async () => {
    let release;
    shardResponse = () => new Promise((r) => { release = () => r({ ok: true, json: () => Promise.resolve(shard) }); });
    renderApp();
    expect(screen.getByTestId('job-description').textContent).toBe('loading…');
    await act(async () => { release(); });
    await vi.waitFor(() => expect(screen.getByTestId('job-description').textContent).not.toBe('loading…'));
  });

  it('offers a retry when the description shard fails, and the retry refetches', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    shardResponse = () => Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({}) });
    renderApp();
    const retry = await screen.findByRole('button', { name: /RETRY/ });
    expectText(screen.getByTestId('job-description'), 'description unavailable');
    shardResponse = () => Promise.resolve({ ok: true, json: () => Promise.resolve(shard) });
    fireEvent.click(retry);
    await vi.waitFor(() => expect(screen.getByTestId('job-description').textContent).not.toMatch(/unavailable|loading/));
  });

  it('the row star is a mouse shortcut, not a control nested in the option (axe nested-interactive)', () => {
    renderApp();
    const row = selectedRow();
    expect(row.querySelector('button, a[href], input, [tabindex]')).toBeNull();
    const star = row.lastElementChild;
    expect(star.getAttribute('aria-hidden')).toBe('true');
    expect(star.textContent).toBe('☆');
    fireEvent.click(star);
    expect(JSON.parse(window.localStorage.getItem(SAVED_STORAGE_KEY))).toEqual([row.dataset.jobId]);
    // The click saved without also re-selecting a different row.
    expect(selectedRow().dataset.jobId).toBe(row.dataset.jobId);
  });

  it('APPLY is a real new-tab link with a safe http(s) href', () => {
    renderApp();
    const apply = screen.getByRole('link', { name: /APPLY/ });
    expect(apply.getAttribute('href')).toMatch(/^https:\/\//);
    expect(apply.getAttribute('target')).toBe('_blank');
    expect(apply.getAttribute('rel')).toBe('noopener noreferrer');
    expect(screen.queryByText(/REFER A FRIEND/)).toBeNull();
  });

  it('never renders invented data (deadlines, stack, cohort, fake deltas, "sponsored")', () => {
    renderApp();
    const text = document.body.textContent;
    for (const bad of ['DEADLINE', 'CLOSING', 'COHORT', 'STACK', '+2.1%', '+12 24h', 'sponsored', 'base + equity', 'STATUS: OK']) {
      expect(text).not.toContain(bad);
    }
    expect(screen.getByRole('group', { name: 'COMPANY TIER' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: '<50' })).toBeNull();
  });

  it('SIMILAR ROLES are real jobs of the same type and select that job', () => {
    renderApp();
    const detail = screen.getByTestId('job-detail');
    const similar = within(detail).getAllByRole('button').filter((b) => b.closest('li'));
    expect(similar.length).toBeGreaterThan(0);
    fireEvent.click(similar[0]);
    expect(within(screen.getByTestId('job-detail')).getByRole('heading', { level: 2 }).textContent)
      .toBe(similar[0].textContent.split(' · ')[1]);
  });

  it('search + company facet filter, and Esc clears everything without crashing', () => {
    renderApp();
    fireEvent.change(screen.getByLabelText('Search jobs'), { target: { value: 'twilio' } });
    const twilio = rows().length;
    expect(twilio).toBeGreaterThan(0);
    expect(twilio).toBeLessThan(20);
    fireEvent.change(screen.getByLabelText('Search jobs'), { target: { value: '' } });
    fireEvent.click(screen.getByTitle('filter to Palantir'));
    expect(rows().length).toBeLessThan(20);
    rows().forEach((r) => expectText(r, 'Palantir'));
    key('Escape');
    expect(rows()).toHaveLength(20);
    expect(screen.getByRole('status').textContent).toBe('filters cleared');
  });

  it('chips expose aria-pressed and the visa facet is honestly labelled', () => {
    renderApp();
    const chip = screen.getByRole('button', { name: 'no restriction stated' });
    expect(chip.getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(chip);
    expect(chip.getAttribute('aria-pressed')).toBe('true');
  });

  it('shortcuts stand aside for focused buttons, inputs and modifier keys', () => {
    renderApp();
    const first = selectedRow().dataset.jobId;
    const chip = screen.getByRole('button', { name: 'swe' });
    key('j', {}, chip);
    key('j', { ctrlKey: true });
    key('j', {}, screen.getByLabelText('Search jobs'));
    expect(selectedRow().dataset.jobId).toBe(first);
    key('j', {}, listbox());
    expect(selectedRow().dataset.jobId).not.toBe(first);
  });

  it('? and F1 open the help dialog; Esc closes it and returns focus', () => {
    renderApp();
    listbox().focus();
    key('F1');
    const dialog = screen.getByRole('dialog', { name: /keyboard shortcuts/i });
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.contains(document.activeElement)).toBe(true);
    key('Escape', {}, document.activeElement);
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(listbox());
    // Esc inside the dialog must not also clear filters.
    expect(screen.getByRole('status').textContent).toBe('');
    key('?');
    expect(screen.getByRole('dialog')).toBeTruthy();
  });

  it('S saves the selected job; saved jobs persist by job_id across remounts', () => {
    const { unmount } = renderApp();
    const id = selectedRow().dataset.jobId;
    key('s');
    expect(JSON.parse(window.localStorage.getItem(SAVED_STORAGE_KEY))).toEqual([id]);
    unmount();
    renderApp();
    expect(rows().find((r) => r.dataset.jobId === id).getAttribute('aria-label')).toMatch(/saved$/);
    fireEvent.click(screen.getByRole('button', { name: /SAVED: 1/ }));
    expect(rows()).toHaveLength(1);
  });

  it('survives corrupt or unavailable localStorage', () => {
    window.localStorage.setItem(SAVED_STORAGE_KEY, '{not json');
    window.localStorage.setItem = () => { throw new Error('QuotaExceeded'); };
    renderApp();
    key('s');
    expect(screen.getByRole('button', { name: /SAVED: 1/ })).toBeTruthy();
  });

  it('writes filters, search, sort and selection to the URL and restores them on load', async () => {
    const { unmount } = renderApp();
    fireEvent.change(screen.getByLabelText('Search jobs'), { target: { value: 'engineer' } });
    fireEvent.click(screen.getByRole('button', { name: 'remote' }));
    fireEvent.click(screen.getByRole('button', { name: /^COMP, / }));
    key('j');
    const picked = selectedRow().dataset.jobId;
    await flushUrl();
    expect(params().get('q')).toBe('engineer');
    expect(params().getAll('remote')).toEqual(['remote']);
    expect(params().get('sort')).toBe('comp-desc');
    expect(params().get('job')).toBe(picked);
    unmount();

    renderApp();
    expect(screen.getByLabelText('Search jobs').value).toBe('engineer');
    expect(screen.getByRole('button', { name: 'remote' }).getAttribute('aria-pressed')).toBe('true');
    expect(selectedRow().dataset.jobId).toBe(picked);
    expectText(screen.getByRole('button', { name: /^COMP, / }), '▼');
  });

  it('sort arrows: ▲ ascending, ▼ descending, consistently', () => {
    renderApp();
    const co = screen.getByRole('button', { name: /^CO, / });
    fireEvent.click(co);
    expectText(co, '▲');
    const names = rows().map((r) => r.getAttribute('aria-label').split(',')[0]);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' })));
    fireEvent.click(co);
    expectText(co, '▼');
  });

  it('renders the load-error state instead of an empty dashboard', () => {
    renderApp({ jobs: [], meta: {}, error: 'jobs.json: HTTP 500' });
    expectText(screen.getByRole('alert'), "COULDN'T LOAD JOBS");
    expectText(screen.getByRole('tab', { name: /HIRING/ }), 'offline');
  });

  it('copes with an empty feed (no selection, Esc safe)', () => {
    renderApp({ jobs: [], meta: {}, error: null });
    expect(screen.getByText(/No open roles in the feed/)).toBeTruthy();
    key('Escape');
    key('j');
    expect(screen.getByText(/NO MATCHES/)).toBeTruthy();
  });

  it('marks closed jobs and leaves them out of the OPEN count', () => {
    const payload = { ...rawJobs, jobs: rawJobs.jobs.map((j, i) => (i === 0 ? { ...j, is_closed: true } : j)) };
    renderApp({ ...normalizeJobsPayload(payload), error: null });
    expectText(screen.getByRole('tab', { name: /HIRING/ }), '19 open');
    expect(screen.getAllByText('CLOSED').length).toBeGreaterThan(0);
  });
});

describe('mobile', () => {
  beforeEach(() => mockMatchMedia(true));

  it('cards hold sibling buttons (no nested interactive) and open a modal detail', () => {
    renderApp();
    const cards = rows();
    expect(cards.length).toBeGreaterThan(0);
    const open = cards[0];
    expect(open.tagName).toBe('BUTTON');
    expect(open.querySelector('button')).toBeNull();
    fireEvent.click(open);
    const dialog = screen.getByRole('dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(params().get('job')).toBe(open.dataset.jobId);
    expect(window.history.state).toEqual({ ngjDetail: true });
  });

  it('the horizontally scrolling stats strip is keyboard-focusable (axe scrollable-region-focusable)', () => {
    renderApp();
    expect(screen.getByRole('region', { name: 'Feed statistics' }).getAttribute('tabindex')).toBe('0');
  });

  it('the browser back button closes the detail', () => {
    renderApp();
    fireEvent.click(rows()[0]);
    expect(screen.getByRole('dialog')).toBeTruthy();
    act(() => {
      window.history.replaceState(null, '', '/');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('BACK on a deep-linked detail (nothing to pop) just closes it', () => {
    const id = jobsState.jobs[3].id;
    window.history.replaceState(null, '', `/?job=${id}`);
    renderApp();
    const back = screen.getByRole('button', { name: 'Back to job list' });
    fireEvent.click(back);
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});

describe('contributors tab', () => {
  it('shows the roster once contributors resolve, and keeps hiring filters on return', async () => {
    renderApp();
    fireEvent.change(screen.getByLabelText('Search jobs'), { target: { value: 'twilio' } });
    fireEvent.click(screen.getByRole('tab', { name: /CONTRIBUTORS/ }));
    expect(params().get('tab')).toBe('contributors');
    const list = await screen.findByText(/SHOWN:/);
    expect(within(list.parentElement).getByText('3')).toBeTruthy();
    fireEvent.click(screen.getByRole('tab', { name: /HIRING/ }));
    expect(screen.getByLabelText('Search jobs').value).toBe('twilio');
  });

  it('maps a legacy #contributors link to ?tab=contributors', async () => {
    window.history.replaceState(null, '', '/#contributors');
    renderApp();
    expect(screen.getByRole('tab', { name: /CONTRIBUTORS/ }).getAttribute('aria-selected')).toBe('true');
    await flushUrl();
    expect(window.location.hash).toBe('');
    expect(params().get('tab')).toBe('contributors');
  });
});

describe('new-roles window (?new=<hours>)', () => {
  // The fixture predates first_seen; stamp the first five jobs as seen an hour before the feed was generated.
  const generated = Date.parse(rawJobs.meta.generated_at);
  const stamped = {
    ...rawJobs,
    jobs: rawJobs.jobs.map((j, i) => ({ ...j, first_seen: new Date(generated - (i < 5 ? 1 : 48) * 3600e3).toISOString() })),
  };
  const recentState = { ...normalizeJobsPayload(stamped), error: null };

  it('shows only roles first seen in the window, with a chip that clears it and keeps utm tags', async () => {
    window.history.replaceState(null, '', '/?new=24&utm_source=newsletter');
    renderApp(recentState);
    expect(rows()).toHaveLength(5);
    const chip = screen.getByRole('button', { name: /added in last 24h/ });
    act(() => { fireEvent.click(chip); });
    expect(rows()).toHaveLength(20);
    await flushUrl();
    expect(params().get('new')).toBeNull();
    expect(params().get('utm_source')).toBe('newsletter');
  });
});
