// @vitest-environment jsdom
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DEFAULT_REPO, applyGhEnrichment, buildGhPayload, mapContributor } from '../../lib/contributors.js';
import { ContributorsView } from './ContributorsView.jsx';
import { RECENT_COMMITS_DEBOUNCE_MS, useRecentCommits } from './useRecentCommits.js';
import { stepHandle } from './useContribKeys.js';

const raw = JSON.parse(readFileSync(resolve(process.cwd(), 'test/fixtures/contributors.json'), 'utf8')).contributors;

const IDLE = Object.freeze({ state: 'loading', commits: [] });
function fakeStore() {
  return { ensure: vi.fn(), subscribe: vi.fn(() => () => {}), get: vi.fn(() => IDLE) };
}

beforeEach(() => {
  window.matchMedia = vi.fn(() => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }));
  globalThis.fetch = vi.fn(() => Promise.resolve({ ok: false, status: 404, headers: { get: () => null }, json: () => Promise.resolve({}) }));
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe('useRecentCommits', () => {
  it('only fetches once the selection settles (debounced)', () => {
    vi.useFakeTimers();
    const store = fakeStore();
    const { rerender } = renderHook(({ h }) => useRecentCommits(h, { store }), { initialProps: { h: 'a' } });
    rerender({ h: 'b' });
    rerender({ h: 'c' });
    act(() => { vi.advanceTimersByTime(RECENT_COMMITS_DEBOUNCE_MS - 1); });
    expect(store.ensure).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1); });
    expect(store.ensure).toHaveBeenCalledTimes(1);
    expect(store.ensure).toHaveBeenCalledWith('c');
  });

  it('does nothing without a handle', () => {
    vi.useFakeTimers();
    const store = fakeStore();
    const { result } = renderHook(() => useRecentCommits(null, { store }));
    act(() => { vi.advanceTimersByTime(1000); });
    expect(store.ensure).not.toHaveBeenCalled();
    expect(result.current.state).toBe('loading');
  });
});

describe('stepHandle', () => {
  const list = [{ handle: 'a' }, { handle: 'b' }];
  it('moves and clamps', () => {
    expect(stepHandle(list, 'a', 1)).toBe('b');
    expect(stepHandle(list, 'b', 1)).toBe('b');
    expect(stepHandle(list, 'a', -1)).toBe('a');
    expect(stepHandle(list, 'zzz', 1)).toBe('a');
    expect(stepHandle([], 'x', 1)).toBe('x');
  });
});

describe('ContributorsView', () => {
  const renderView = (gh) => {
    const state = applyGhEnrichment(raw.map(mapContributor), DEFAULT_REPO, gh);
    render(<ContributorsView contributorsPromise={Promise.resolve(state)} />);
    return state;
  };

  it('shows only real data: no invented deltas, LoC, CODEOWNERS paths or languages', async () => {
    renderView(null);
    await screen.findByText(/SHOWN:/);
    const text = document.body.textContent;
    expect(text).not.toMatch(/\+412|\+98|NET LOC|src\/\w+\/\*\*|ACTIVITY · 26W|Rust|rust/);
    expect(screen.getByText('commit counts unavailable')).toBeTruthy();
    // Chip options are the contribution types present in the fixture.
    expect(screen.getByText('CONTRIBUTION')).toBeTruthy();
    expect(screen.queryByText('LANGUAGE')).toBeNull();
  });

  it('renders GitHub languages and commit counts when available', async () => {
    const gh = buildGhPayload({ stargazers_count: 1234 }, raw.map((c, i) => ({ login: c.login, contributions: 10 - i })), { total_count: 4 }, { Python: 9, JavaScript: 1 });
    renderView(gh);
    await screen.findByText(/SHOWN:/);
    expect(screen.getByText('Python 90%')).toBeTruthy();
    expect(screen.getByText('JavaScript 10%')).toBeTruthy();
    expect(screen.getByText('TOP BY COMMITS').parentElement.textContent).toMatch(/1@/);
  });

  it('TOP BY COMMITS rows meet the 24px target size (WCAG 2.5.8)', async () => {
    const gh = buildGhPayload({}, raw.map((c, i) => ({ login: c.login, contributions: 10 - i })), null, null);
    renderView(gh);
    await screen.findByText(/SHOWN:/);
    const board = screen.getByText('TOP BY COMMITS').parentElement;
    const buttons = [...board.querySelectorAll('button')];
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((b) => expect(parseFloat(b.style.minHeight)).toBeGreaterThanOrEqual(24));
  });

  it('sponsor link only for handles with GitHub Sponsors; profile is a real link', async () => {
    renderView(null);
    await screen.findByText(/SHOWN:/);
    const sel = () => document.body.textContent.match(/SEL: @([A-Za-z0-9-]+)/)[1];
    expect(sel()).toBe('ambicuity');
    expect(screen.getByText('SPONSOR ↗').getAttribute('href')).toBe('https://github.com/sponsors/ambicuity');
    act(() => { fireEvent.keyDown(window, { key: 'j' }); });
    expect(sel()).not.toBe('ambicuity');
    expect(screen.queryByText('SPONSOR ↗')).toBeNull();
    expect(screen.getByText('VIEW ON GITHUB ↗').getAttribute('href')).toBe(`https://github.com/${sel()}`);
  });

  it('j/k move the selection and / focuses search', async () => {
    renderView(null);
    await screen.findByText(/SHOWN:/);
    const sel = () => document.body.textContent.match(/SEL: @([A-Za-z0-9-]+)/)[1];
    const first = sel();
    act(() => { fireEvent.keyDown(window, { key: 'j' }); });
    expect(sel()).not.toBe(first);
    act(() => { fireEvent.keyDown(window, { key: 'k' }); });
    expect(sel()).toBe(first);
    act(() => { fireEvent.keyDown(window, { key: '/' }); });
    expect(document.activeElement).toBe(screen.getByLabelText('Search contributors'));
  });
});
