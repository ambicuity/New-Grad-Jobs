// Contributors / GitHub data sources are covered in contributors-source.test.js.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadJobs } from './jobs-source.js';
import { createShardLoader } from './descriptions-source.js';

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

  it('rejects on failure (so the UI can offer a retry) and refetches on the next call', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const f = routeFetch({});
    const load = createShardLoader(f);
    await expect(load('b')).rejects.toThrow('descriptions/b.json: HTTP 404');
    await expect(load('b')).rejects.toThrow();
    expect(f).toHaveBeenCalledTimes(2);
  });

  it('rejects a shard that is not a JSON object', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const load = createShardLoader(routeFetch({ 'descriptions/c.json': () => ok(['nope']) }));
    await expect(load('c')).rejects.toThrow(/not an object/);
  });
});
