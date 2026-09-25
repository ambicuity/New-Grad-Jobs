// Contributors / GitHub data sources are covered in contributors-source.test.js.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { brotliCompressSync } from 'node:zlib';
import { brotliStreamSupported, fetchJsonPreferBrotli, loadExtendedJobs, loadJobs } from './jobs-source.js';
import { createShardLoader } from './descriptions-source.js';
import { loadCorpus } from './corpus-source.js';

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
    const out = await loadJobs(f, false);
    expect(out.error).toBeNull();
    expect(out.encoding).toBe('gzip');
    expect(out.meta.generated_at).toBe('g');
    expect(out.jobs.map((j) => j.id)).toEqual(['a']);
    expect(f).toHaveBeenCalledWith('./jobs-index.json', { cache: 'no-cache' });
  });

  it('falls back to jobs.json when the index is missing', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const f = routeFetch({ 'jobs.json': () => ok({ jobs: [{ id: 'b' }] }) });
    const out = await loadJobs(f, false);
    expect(out.jobs.map((j) => j.id)).toEqual(['b']);
    expect(f).toHaveBeenCalledTimes(2);
  });

  it('resolves with an error (never rejects) when both fail', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const out = await loadJobs(routeFetch({}), false);
    expect(out).toEqual({ jobs: [], meta: {}, error: 'jobs.json: HTTP 404', encoding: null });
  });

  it('reports a malformed payload', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const out = await loadJobs(routeFetch({ 'jobs-index.json': () => ok({ nope: 1 }) }), false);
    expect(out.error).toMatch(/no "jobs" array/);
  });
});

describe('loadExtendedJobs', () => {
  it('loads the near-miss tier with its reasons', async () => {
    const f = routeFetch({ 'jobs-extended.json': () => ok({ meta: { tier: 'near_miss' }, jobs: [{ job_id: 'job_n1', near_miss: { reasons: ['intern_or_coop'] } }] }) });
    const out = await loadExtendedJobs(f, false);
    expect(out.error).toBeNull();
    expect(out.meta.tier).toBe('near_miss');
    expect(out.jobs[0].nearMiss).toEqual(['intern_or_coop']);
    expect(f).toHaveBeenCalledWith('./jobs-extended.json', { cache: 'no-cache' });
  });

  it('resolves with no jobs and an error when the file is missing', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    expect(await loadExtendedJobs(routeFetch({}), false)).toEqual({ jobs: [], meta: {}, error: 'jobs-extended.json: HTTP 404', encoding: null });
  });
});

describe('Brotli data siblings', () => {
  const payload = { meta: { generated_at: 'g' }, jobs: [{ job_id: 'job_br1' }] };
  const brBody = () => new Response(brotliCompressSync(Buffer.from(JSON.stringify(payload)))).body;
  const brOk = () => Promise.resolve({ ok: true, status: 200, body: brBody() });

  it('feature-detects the native decoder', () => {
    expect(brotliStreamSupported()).toBe(true); // Node ships DecompressionStream('brotli')
    expect(brotliStreamSupported({})).toBe(false);
    expect(brotliStreamSupported({ DecompressionStream: function Nope() { throw new TypeError('no'); } })).toBe(false);
  });

  it('decodes the .br sibling natively and reports the encoding', async () => {
    const f = vi.fn((url) => (url.endsWith('.br') ? brOk() : fail(404)));
    const out = await fetchJsonPreferBrotli('./jobs-index.json', f, true);
    expect(out).toEqual({ data: payload, encoding: 'br' });
    expect(f).toHaveBeenCalledTimes(1);
    expect(f).toHaveBeenCalledWith('./jobs-index.json.br', { cache: 'no-cache' });
    const loaded = await loadJobs(f, true);
    expect(loaded.encoding).toBe('br');
    expect(loaded.jobs[0].id).toBe('job_br1');
  });

  it('falls back to the gzip json when the sibling is missing, unsupported or corrupt', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const missing = routeFetch({ 'jobs-index.json': () => ok(payload) });
    expect((await fetchJsonPreferBrotli('./jobs-index.json', missing, true)).encoding).toBe('gzip');
    const unsupported = vi.fn(() => ok(payload));
    expect((await fetchJsonPreferBrotli('./jobs-index.json', unsupported, false)).encoding).toBe('gzip');
    expect(unsupported).toHaveBeenCalledWith('./jobs-index.json', { cache: 'no-cache' });
    const corrupt = vi.fn((url) => (url.endsWith('.br')
      ? Promise.resolve({ ok: true, status: 200, body: new Response(Buffer.from('not brotli at all')).body })
      : ok(payload)));
    expect((await fetchJsonPreferBrotli('./jobs-index.json', corrupt, true)).encoding).toBe('gzip');
  });
});

describe('loadCorpus', () => {
  const payload = { meta: { total: 1, fields: ['company', 'title', 'location', 'source', 'posted_at', 'category', 'tier', 'url'] },
    rows: [['Acme', 'Rust Engineer', 'Austin, TX', 'Greenhouse', '2026-09-20', 'software_engineering', 2, 'https://a.test/1']] };

  it('loads and parses the corpus rows', async () => {
    const out = await loadCorpus(routeFetch({ 'corpus-index.json': () => ok(payload) }), false);
    expect(out.error).toBeNull();
    expect(out.encoding).toBe('gzip');
    expect(out.rows[0]).toMatchObject({ co: 'Acme', title: 'Rust Engineer', tier: 'out' });
  });

  it('never rejects: a missing file resolves with an error and no rows', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    expect(await loadCorpus(routeFetch({}), false)).toEqual({ rows: [], meta: {}, error: 'corpus-index.json: HTTP 404', encoding: null });
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
