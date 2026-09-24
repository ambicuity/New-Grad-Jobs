// @vitest-environment jsdom
// Smoke tests for the rendered views against the fixture dataset.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { normalizeJobsPayload } from '../lib/jobs.js';
import { applyGhEnrichment, DEFAULT_REPO, mapContributor } from '../lib/contributors.js';
import { App } from './shell/App.jsx';

// Vitest runs from site/, and import.meta.url is not a file: URL under jsdom.
const fixture = (rel) => JSON.parse(readFileSync(resolve(process.cwd(), 'test/fixtures', rel), 'utf8'));
const jobsState = { ...normalizeJobsPayload(fixture('jobs-index.json')), error: null };
const contributorsState = applyGhEnrichment(fixture('contributors.json').contributors.map(mapContributor), DEFAULT_REPO, null);
const shard = fixture('descriptions/a.json');

function mockMatchMedia(mobile) {
  window.matchMedia = vi.fn(() => ({ matches: mobile, addEventListener: () => {}, removeEventListener: () => {} }));
}

beforeEach(() => {
  window.location.hash = '';
  mockMatchMedia(false);
  globalThis.fetch = vi.fn((url) => {
    if (String(url).includes('descriptions/a.json')) return Promise.resolve({ ok: true, json: () => Promise.resolve(shard) });
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
  });
});
afterEach(() => cleanup());

const renderApp = (state = jobsState) => render(
  <App jobsState={state} contributorsPromise={Promise.resolve(contributorsState)} />,
);
const rows = () => [...document.querySelectorAll('[data-testid="job-list"] > [data-job-id]')];
const selectedRow = () => document.querySelector('[data-testid="job-list"] > [aria-selected="true"]');
const expectText = (el, text) => {
  if (text instanceof RegExp) expect(el.textContent).toMatch(text);
  else expect(el.textContent).toContain(text);
};
const key = (k) => act(() => { fireEvent.keyDown(window, { key: k }); });

describe('hiring view (desktop)', () => {
  it('renders every fixture job and the tab counts', async () => {
    renderApp();
    expect(rows()).toHaveLength(20);
    expectText(screen.getByRole('tab', { name: /HIRING/ }), '20 open');
    await screen.findByText('3 devs');
  });

  it('j/k move the selection and the detail pane lazy-loads the description', async () => {
    renderApp();
    const first = selectedRow().dataset.jobId;
    key('j');
    const second = selectedRow().dataset.jobId;
    expect(second).not.toBe(first);
    key('k');
    expect(selectedRow().dataset.jobId).toBe(first);
    const job = jobsState.jobs.find((j) => j.id === first);
    const expected = shard[job.jobId];
    await vi.waitFor(() => expect(screen.getByTestId('job-description').textContent).toBe(expected));
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
    expect(screen.getByText('filters cleared')).toBeTruthy();
  });

  it('? opens the help overlay and Esc closes it', () => {
    renderApp();
    key('?');
    expect(screen.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeTruthy();
    key('Escape');
    expect(screen.queryByRole('dialog')).toBeNull();
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
});

describe('mobile', () => {
  it('tapping a card opens the full-screen detail and BACK returns', () => {
    mockMatchMedia(true);
    renderApp();
    fireEvent.click(rows()[0]);
    const back = screen.getByRole('button', { name: 'Back to job list' });
    expect(back).toBeTruthy();
    fireEvent.click(back);
    expect(screen.queryByRole('button', { name: 'Back to job list' })).toBeNull();
  });
});

describe('contributors tab', () => {
  it('shows the roster once contributors resolve', async () => {
    renderApp();
    fireEvent.click(screen.getByRole('tab', { name: /CONTRIBUTORS/ }));
    expect(window.location.hash).toBe('#contributors');
    const list = await screen.findByText(/SHOWN:/);
    expect(within(list.parentElement).getByText('3')).toBeTruthy();
  });
});
