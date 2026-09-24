import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  fetchGitHubMeta, loadContributors, readCacheEntry, readGhCache, writeCacheEntry, writeGhCache,
} from './contributors-source.js';
import { createRecentCommitsStore, retryAtFromHeaders } from './recent-commits.js';

const headers = (h = {}) => ({ get: (k) => h[k.toLowerCase()] ?? null });
const ok = (body) => Promise.resolve({ ok: true, status: 200, headers: headers(), json: () => Promise.resolve(body) });
const fail = (status, h) => Promise.resolve({ ok: false, status, headers: headers(h), json: () => Promise.resolve({}) });

function routeFetch(routes) {
  return vi.fn((url) => {
    const hit = Object.keys(routes).find((k) => url.includes(k));
    return hit ? routes[hit]() : fail(404);
  });
}

const memStore = () => {
  const m = new Map();
  return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v), map: m };
};

const PAYLOAD = { repo: { stars: 1 }, contribs: [{ login: 'a', contributions: 3 }] };

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('GitHub cache', () => {
  it('round-trips a valid payload within the TTL and expires after an hour', () => {
    const s = memStore();
    writeGhCache(PAYLOAD, s, 1000);
    expect(readGhCache(s, 1000 + 60 * 1000)).toEqual(PAYLOAD);
    expect(readGhCache(s, 1000 + 61 * 60 * 1000)).toBeNull();
  });

  it('ignores malformed or wrongly-shaped entries', () => {
    expect(readGhCache(null)).toBeNull();
    expect(readGhCache({ getItem: () => '{bad json' })).toBeNull();
    expect(readGhCache({ getItem: () => JSON.stringify({ t: 'x', data: PAYLOAD }) })).toBeNull();
    expect(readGhCache({ getItem: () => JSON.stringify({ t: 1, data: { x: 1 } }) }, 2)).toBeNull();
    expect(readGhCache({ getItem: () => JSON.stringify({ t: 5000, data: PAYLOAD }) }, 1000)).toBeNull(); // from the future
    expect(readCacheEntry('k', () => true, { store: { getItem: () => 'null' } })).toBeNull();
  });

  it('write failures only warn', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    writeCacheEntry('k', {}, { store: { setItem: () => { throw new Error('quota'); } } });
    expect(warn).toHaveBeenCalled();
  });
});

describe('fetchGitHubMeta / loadContributors', () => {
  const CONTRIBS = { contributors: [{ login: 'ambicuity', name: 'R', contributions: ['code'] }, { login: 'dev', contributions: ['doc'] }] };

  it('builds the payload from the four API calls, including real languages', async () => {
    const f = routeFetch({
      '/contributors?': () => ok([{ login: 'dev', contributions: 900 }]),
      '/search/issues': () => ok({ total_count: 3 }),
      '/languages': () => ok({ Python: 3, JavaScript: 1 }),
      '/repos/ambicuity/New-Grad-Jobs': () => ok({ stargazers_count: 42 }),
    });
    const gh = await fetchGitHubMeta(f);
    expect(gh.repo).toMatchObject({ stars: 42, prs_open: 3, langs: [['Python', 75], ['JavaScript', 25]] });
    expect(gh.contribs).toEqual([{ login: 'dev', contributions: 900 }]);
    expect(f).toHaveBeenCalledTimes(4);
  });

  it('returns null when the API is unavailable or throws', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    await expect(fetchGitHubMeta(routeFetch({}))).resolves.toBeNull();
    await expect(fetchGitHubMeta(() => Promise.reject(new Error('offline')))).resolves.toBeNull();
  });

  it('gives up after the timeout (aborts hanging requests)', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const hang = (_url, opts) => new Promise((_resolve, reject) => {
      opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
    });
    await expect(fetchGitHubMeta(hang, 10)).resolves.toBeNull();
  });

  it('loadContributors merges real commit counts; unknown stays null', async () => {
    const f = routeFetch({
      'contributors.json': () => ok(CONTRIBS),
      '/contributors?': () => ok([{ login: 'dev', contributions: 5000 }]),
      '/search/issues': () => fail(403),
      '/languages': () => fail(403),
      '/repos/ambicuity/New-Grad-Jobs': () => ok({ stargazers_count: 7 }),
    });
    const out = await loadContributors(f);
    expect(out.contributors.map((c) => [c.handle, c.commits])).toEqual([['dev', 5000], ['ambicuity', null]]);
    expect(out.repo.stars).toBe(7);
    expect(out.repo.prs_open).toBeNull();
    expect(out.repo.langs).toEqual([]);
  });

  it('loadContributors resolves empty on failure', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const out = await loadContributors(routeFetch({}));
    expect(out.contributors).toEqual([]);
    expect(out.repo.name).toBe('ambicuity/New-Grad-Jobs');
  });
});

describe('recent commits store', () => {
  const COMMIT = { sha: 'abcdef1234', commit: { message: 'fix: y', author: { date: '2026-01-01T00:00:00Z' } }, html_url: 'https://github.com/o/r/commit/abcdef1' };

  it('fetches once per handle, notifies subscribers and persists to localStorage', async () => {
    const f = vi.fn(() => ok([COMMIT]));
    const store = memStore();
    const s = createRecentCommitsStore({ fetchImpl: f, store, now: () => 1000 });
    const cb = vi.fn();
    const unsub = s.subscribe('dev', cb);
    expect(s.get('dev').state).toBe('loading');
    s.ensure('dev');
    s.ensure('dev');
    await vi.waitFor(() => expect(s.get('dev').state).toBe('ok'));
    expect(s.get('dev').commits).toEqual([{ sha: 'abcdef1', msg: 'fix: y', date: '2026-01-01T00:00:00Z', url: 'https://github.com/o/r/commit/abcdef1' }]);
    expect(f).toHaveBeenCalledTimes(1);
    expect(cb).toHaveBeenCalled();
    expect([...store.map.keys()]).toEqual(['ng-terminal:gh-commits-v1:dev']);
    unsub();

    // A fresh session reads the persisted rows without hitting the network.
    const f2 = vi.fn(() => ok([]));
    const s2 = createRecentCommitsStore({ fetchImpl: f2, store, now: () => 2000 });
    s2.ensure('dev');
    expect(s2.get('dev').state).toBe('ok');
    expect(f2).not.toHaveBeenCalled();
  });

  it('ignores expired or malformed persisted rows', async () => {
    const store = memStore();
    store.setItem('ng-terminal:gh-commits-v1:dev', JSON.stringify({ t: 0, data: [{ sha: 'bad' }] }));
    const f = vi.fn(() => ok([]));
    const s = createRecentCommitsStore({ fetchImpl: f, store, now: () => 10 });
    s.ensure('dev');
    await vi.waitFor(() => expect(s.get('dev').state).toBe('empty'));
    expect(f).toHaveBeenCalledTimes(1);
  });

  it('rate limits: not persisted, no retry before the reset time, retried after', async () => {
    let t = 1_000_000;
    const store = memStore();
    const f = vi.fn()
      .mockImplementationOnce(() => fail(403, { 'x-ratelimit-remaining': '0', 'x-ratelimit-reset': String((t + 60_000) / 1000) }))
      .mockImplementation(() => ok([COMMIT]));
    const s = createRecentCommitsStore({ fetchImpl: f, store, now: () => t });
    s.ensure('dev');
    await vi.waitFor(() => expect(s.get('dev').state).toBe('error'));
    expect(s.get('dev')).toMatchObject({ error: 'github rate limit reached', retryAt: t + 60_000 });
    expect(store.map.size).toBe(0);
    s.ensure('dev');
    expect(f).toHaveBeenCalledTimes(1);
    t += 61_000;
    s.ensure('dev');
    await vi.waitFor(() => expect(s.get('dev').state).toBe('ok'));
    expect(f).toHaveBeenCalledTimes(2);
  });

  it('other errors are retried on the next ensure; empty results recorded', async () => {
    const f = vi.fn((url) => (url.includes('author=none') ? ok([]) : fail(500)));
    const s = createRecentCommitsStore({ fetchImpl: f, store: memStore() });
    s.ensure('none');
    s.ensure('bad');
    await vi.waitFor(() => expect(s.get('bad').state).toBe('error'));
    expect(s.get('bad').error).toBe('gh api 500');
    expect(s.get('none').state).toBe('empty');
    s.ensure('bad');
    await vi.waitFor(() => expect(f).toHaveBeenCalledTimes(3));
    const s2 = createRecentCommitsStore({ fetchImpl: () => Promise.reject(new Error('offline')), store: null });
    s2.ensure('x');
    await vi.waitFor(() => expect(s2.get('x')).toMatchObject({ state: 'error', error: 'offline' }));
  });

  it('retryAtFromHeaders prefers retry-after, then x-ratelimit-reset, then a default', () => {
    expect(retryAtFromHeaders(headers({ 'retry-after': '30' }), 1000)).toBe(31_000);
    expect(retryAtFromHeaders(headers({ 'x-ratelimit-reset': '100' }), 1000)).toBe(100_000);
    expect(retryAtFromHeaders(headers({}), 1000)).toBe(61_000);
    expect(retryAtFromHeaders(undefined, 0)).toBe(60_000);
  });
});
