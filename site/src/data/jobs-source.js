// Fetches the jobs payload. jobs-index.json is jobs.json minus descriptions
// (a fraction of the size); fall back to the full jobs.json if the index is
// missing, e.g. while a deploy lands before the scraper has published it.
//
// Compression: GitHub Pages only gzips. The build also publishes a Brotli
// sibling (`<file>.json.br`, ~40% smaller than the host's gzip) which this
// module fetches first when the browser can decode it natively
// (DecompressionStream('brotli')); any failure falls back to the plain
// `.json`, which the host serves gzipped. See scripts/seo/compress.mjs.

import { normalizeJobsPayload } from '../lib/jobs.js';

export const JOBS_INDEX_URL = './jobs-index.json';
export const JOBS_FULL_URL = './jobs.json';
/** The near-miss tier (scripts/ngj/outputs/jobs_json.py generate_extended_json); fetched only when a WIDEN SCOPE toggle is on. */
export const JOBS_EXTENDED_URL = './jobs-extended.json';

export async function fetchJson(url, fetchImpl = fetch) {
  const r = await fetchImpl(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${url.replace(/^\.\//, '')}: HTTP ${r.status}`);
  return r.json();
}

export const BROTLI_SUFFIX = '.br';

/** Whether this browser can decode Brotli streams itself (Safari 18.4+, recent Chromium/Firefox). */
export function brotliStreamSupported(global = globalThis) {
  try {
    return typeof global.DecompressionStream === 'function' && Boolean(new global.DecompressionStream('brotli'));
  } catch {
    return false;
  }
}

/**
 * Fetch `url` as JSON, preferring its Brotli sibling. Never throws because of
 * the sibling: a missing or undecodable `.br` just means the plain file.
 * @returns {Promise<{data: any, encoding: 'br'|'gzip'}>}
 */
export async function fetchJsonPreferBrotli(url, fetchImpl = fetch, brotli = brotliStreamSupported()) {
  if (brotli) {
    try {
      const r = await fetchImpl(`${url}${BROTLI_SUFFIX}`, { cache: 'no-cache' });
      if (r && r.ok && r.body && typeof r.body.pipeThrough === 'function') {
        const text = await new Response(r.body.pipeThrough(new DecompressionStream('brotli'))).text();
        return { data: JSON.parse(text), encoding: 'br' };
      }
    } catch (err) {
      console.warn('[terminal] brotli payload unavailable, using the gzip json:', err);
    }
  }
  return { data: await fetchJson(url, fetchImpl), encoding: 'gzip' };
}

/**
 * @typedef {object} JobsState
 * @property {import('../lib/jobs.js').Job[]} jobs
 * @property {import('../lib/jobs.js').JobsMeta} meta
 * @property {string|null} error  Short reason when both payloads failed; null on success (even with 0 jobs).
 * @property {'br'|'gzip'|null} [encoding]  How the payload arrived (null when it failed).
 */

/**
 * Never rejects: a failure resolves with `error` set so the hiring view can
 * render an explicit "couldn't load jobs" state instead of a silent empty list.
 * @returns {Promise<JobsState>}
 */
export async function loadJobs(fetchImpl = fetch, brotli = brotliStreamSupported()) {
  try {
    let payload;
    let encoding = 'gzip';
    try {
      ({ data: payload, encoding } = await fetchJsonPreferBrotli(JOBS_INDEX_URL, fetchImpl, brotli));
    } catch (err) {
      console.warn('[terminal] jobs-index.json unavailable, falling back to jobs.json:', err);
      payload = await fetchJson(JOBS_FULL_URL, fetchImpl);
    }
    const { jobs, meta } = normalizeJobsPayload(payload);
    return { jobs, meta, error: null, encoding };
  } catch (err) {
    console.error('[terminal] failed to load jobs.json:', err);
    return { jobs: [], meta: {}, error: (err && err.message) || String(err), encoding: null };
  }
}

/**
 * Load the near-miss tier. Never rejects: a missing file (older deploy) or a
 * failure resolves with `error` set and no jobs, so the toggles degrade to
 * "nothing extra" instead of breaking the view.
 * @returns {Promise<JobsState>}
 */
export async function loadExtendedJobs(fetchImpl = fetch, brotli = brotliStreamSupported()) {
  try {
    const { data, encoding } = await fetchJsonPreferBrotli(JOBS_EXTENDED_URL, fetchImpl, brotli);
    const { jobs, meta } = normalizeJobsPayload(data);
    return { jobs, meta, error: null, encoding };
  } catch (err) {
    console.warn('[terminal] jobs-extended.json unavailable:', err);
    return { jobs: [], meta: {}, error: (err && err.message) || String(err), encoding: null };
  }
}
