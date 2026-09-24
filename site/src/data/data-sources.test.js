import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadJobs } from './jobs-source.js';
import { createShardLoader } from './descriptions-source.js';
import { fetchGitHubMeta, loadContributors, readGhCache, writeGhCache } from './contributors-source.js';
import { createRecentCommitsStore } from './recent-commits.js';

const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
const fail = (status) => Promise.resolve({ ok: false, status, json: () => Promise.resolve({}) });

function routeFetch(routes) {
  return vi.fn((url) => {
    const hit = Object.keys(routes).find((k) => url.includes(k));
    return hit ? routes[hit]() : fail(404);
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('loadJobs', () => {
  it('loads jobs-index.json', async () => {
    const f = routeFetch({ 'jobs-index.json': () => ok({ meta: { generated_at: 'g' }, jobs: [{ id: 'a' }] }) });
    const out = await loadJobs(f);
    expect(out.error).toBeNull();
    expect(out.meta.generated_at).toBe('g');
    expect(out.jobs.map((j) => j.id)).toEqual(['a']);
    expect(f).toHaveBeenCalledWith('./jobs-index.json', { cache: 'no-cache' });
  });

  it('falls back to jobs.json when the index is missing', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const f = routeFetch({ 'jobs.json': () => ok({ jobs: [{ id: 'b' }] }) });
    const out = await loadJobs(f);
    expect(out.jobs.map((j) => j.id)).toEqual(['b']);
    expect(f).toHaveBeenCalledTimes(2);
  });

  it('resolves with an error (never rejects) when both fail', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const out = await loadJobs(routeFetch({}));
    expect(out).toEqual({ jobs: [], meta: {}, error: 'jobs.json: HTTP 404' });
  });

  it('reports a malformed payload', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const out = await loadJobs(routeFetch({ 'jobs-index.json': () => ok({ nope: 1 }) }));
    expect(out.error).toMatch(/no "jobs" array/);
  });
});

describe('createShardLoader', () => {
  it('fetches each shard once and caches it', async () => {
    const f = routeFetch({ 'descriptions/a.json': () => ok({ job_a1: 'text' }) });
    const load = createShardLoader(f);
    await expect(load('a')).resolves.toEqual({ job_a1: 'text' });
    await load('a');
    expect(f).toHaveBeenCalledTimes(1);
    expect(f).toHaveBeenCalledWith('./descriptions/a.json', { cache: 'no-cache' });
  });

  it('resolves {} on failure and retries on the next call', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const f = routeFetch({});
    const load = createShardLoader(f);
    await expect(load('b')).resolves.toEqual({});
    await load('b');
    expect(f).toHaveBeenCalledTimes(2);
  });
});

describe('GitHub cache', () => {
  const memStore = () => {
    const m = new Map();
    return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) };
  };

  it('round-trips within the TTL and expires after an hour', () => {
    const s = memStore();
    writeGhCache({ x: 1 }, s, 1000);
    expect(readGhCache(s, 1000 + 60 * 1000)).toEqual({ x: 1 });
    expect(readGhCache(s, 1000 + 61 * 60 * 1000)).toBeNull();
  });

  it('tolerates missing storage and corrupt entries', () => {
    expect(readGhCache(null)).toBeNull();
    expect(readGhCache({ getItem: () => '{bad json' })).toBeNull();
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    writeGhCache({}, { setItem: () => { throw new Error('quota'); } });
    expect(warn).toHaveBeenCalled();
  });
});

describe('fetchGitHubMeta / loadContributors', () => {
  const CONTRIBS = { contributors: [{ login: 'ambicuity', name: 'R', contributions: ['code'] }, { login: 'dev', contributions: ['doc'] }] };

  it('builds the payload from the three API calls', async () => {
    const f = routeFetch({
      '/contributors?': () => ok([{ login: 'dev', contributions: 900 }]),
      '/search/issues': () => ok({ total_count: 3 }),
      '/repos/ambicuity/New-Grad-Jobs': () => ok({ stargazers_count: 42 }),
    });
    const gh = await fetchGitHubMeta(f);
    expect(gh.repo).toMatchObject({ stars: 42, prs_open: 3 });
    expect(gh.contribs).toEqual([{ login: 'dev', contributions: 900 }]);
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

  it('loadContributors merges GitHub stats and sorts by commits', async () => {
    const f = routeFetch({
      'contributors.json': () => ok(CONTRIBS),
      '/contributors?': () => ok([{ login: 'dev', contributions: 5000 }]),
      '/search/issues': () => fail(403),
      '/repos/ambicuity/New-Grad-Jobs': () => ok({ stargazers_count: 7 }),
    });
    const out = await loadContributors(f);
    expect(out.contributors.map((c) => c.handle)).toEqual(['dev', 'ambicuity']);
    expect(out.repo.stars).toBe(7);
  });

  it('loadContributors resolves empty on failure', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const out = await loadContributors(routeFetch({}));
    expect(out.contributors).toEqual([]);
    expect(out.repo.name).toBe('ambicuity/New-Grad-Jobs');
  });
});

describe('recent commits store', () => {
  it('fetches once per handle and notifies subscribers', async () => {
    const f = vi.fn(() => ok([{ sha: 'abcdef123', commit: { message: 'fix: y', author: { date: '2026-01-01T00:00:00Z' } } }]));
    const store = createRecentCommitsStore(f);
    const cb = vi.fn();
    const unsub = store.subscribe('dev', cb);
    expect(store.get('dev').state).toBe('loading');
    store.ensure('dev');
    store.ensure('dev');
    await vi.waitFor(() => expect(cb).toHaveBeenCalled());
    expect(store.get('dev')).toMatchObject({ state: 'ok', commits: [{ sha: 'abcdef1', msg: 'fix: y' }] });
    expect(f).toHaveBeenCalledTimes(1);
    unsub();
  });

  it('records empty and error states', async () => {
    const store = createRecentCommitsStore((url) => (url.includes('author=none') ? ok([]) : fail(403)));
    store.ensure('none');
    store.ensure('bad');
    await vi.waitFor(() => expect(store.get('bad').state).toBe('error'));
    expect(store.get('bad').error).toBe('gh api 403');
    expect(store.get('none').state).toBe('empty');
  });
});
