// Fetches the jobs payload. jobs-index.json is jobs.json minus descriptions
// (a fraction of the size); fall back to the full jobs.json if the index is
// missing, e.g. while a deploy lands before the scraper has published it.

import { normalizeJobsPayload } from '../lib/jobs.js';

export const JOBS_INDEX_URL = './jobs-index.json';
export const JOBS_FULL_URL = './jobs.json';

export async function fetchJson(url, fetchImpl = fetch) {
  const r = await fetchImpl(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${url.replace(/^\.\//, '')}: HTTP ${r.status}`);
  return r.json();
}

/**
 * @typedef {object} JobsState
 * @property {import('../lib/jobs.js').Job[]} jobs
 * @property {import('../lib/jobs.js').JobsMeta} meta
 * @property {string|null} error  Short reason when both payloads failed; null on success (even with 0 jobs).
 */

/**
 * Never rejects: a failure resolves with `error` set so the hiring view can
 * render an explicit "couldn't load jobs" state instead of a silent empty list.
 * @returns {Promise<JobsState>}
 */
export async function loadJobs(fetchImpl = fetch) {
  try {
    let payload;
    try {
      payload = await fetchJson(JOBS_INDEX_URL, fetchImpl);
    } catch (err) {
      console.warn('[terminal] jobs-index.json unavailable, falling back to jobs.json:', err);
      payload = await fetchJson(JOBS_FULL_URL, fetchImpl);
    }
    const { jobs, meta } = normalizeJobsPayload(payload);
    return { jobs, meta, error: null };
  } catch (err) {
    console.error('[terminal] failed to load jobs.json:', err);
    return { jobs: [], meta: {}, error: (err && err.message) || String(err) };
  }
}
