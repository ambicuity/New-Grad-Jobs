// Maps the scraper's published job records (jobs-index.json / jobs.json, see
// scripts/publish.py) to the row model the terminal views render.

import { CATEGORY_TYPE, TIER_ORDER } from './taxonomy.js';
import { ageString, parseTimestamp } from './time.js';
import { safeHttpUrl } from './safe-url.js';

/**
 * A job as published in jobs-index.json (jobs.json adds `description`).
 * Every field may be missing on older payloads.
 * @typedef {object} RawJob
 * @property {string} [job_id]        Stable content hash, `job_<hex>`; keys the description shards.
 * @property {string} [id]            Human-readable slug (not unique across sources).
 * @property {string} [company]
 * @property {string} [title]
 * @property {string} [location]
 * @property {string} [url]
 * @property {string} [posted_at]     ISO timestamp (UTC; may lack the `Z`).
 * @property {string} [source]
 * @property {string} [description]   Only in jobs.json.
 * @property {{id?: string, name?: string}} [category]
 * @property {{tier?: string}} [company_tier]
 * @property {{no_sponsorship?: boolean, us_citizenship_required?: boolean}} [flags]
 * @property {boolean} [is_closed]
 * @property {{min?: number, max?: number, currency?: string}|null} [comp]
 */

/**
 * The row model rendered by the hiring view. It carries only what the feed
 * actually publishes — no synthetic deadlines, stacks, cohorts or blurbs.
 * @typedef {object} Job
 * @property {string} id              Stable key: `job_id` when published (else the slug); unique within the list (repeats get `#n`).
 * @property {string} co              Company.
 * @property {string} role            Title.
 * @property {string} loc             Location.
 * @property {string} url             http(s) application URL, or '' (see safeHttpUrl).
 * @property {'remote'|'hybrid'|'onsite'} rmt
 * @property {boolean} visa           True when the posting states NO visa/citizenship restriction
 *                                    (the feed can't tell whether a role actually sponsors).
 * @property {'citizenship'|'no-sponsorship'|null} visaNote  Which restriction the posting states.
 * @property {'faang_plus'|'unicorn'|'other'} tier  company_tier.tier as published.
 * @property {[number|null, number|null]} comp  Posted salary range in $k.
 * @property {string} type            Short category code (SWE, ML, …).
 * @property {string} posted          Display age ("3h", "2d").
 * @property {number} postedTs        Epoch ms of posted_at (0 when unknown).
 * @property {string} jobId           `job_<hex>` or '' — keys the description shards.
 * @property {string} desc            Full description when the payload carries one (jobs.json fallback), else ''.
 * @property {boolean} closed         `is_closed` from the feed.
 * @property {string} hay             Lower-cased search text (company, role, location).
 */

/**
 * @typedef {object} JobsMeta
 * @property {string} [generated_at]
 * @property {number} [total_jobs]
 */

const MIN_REAL_DESCRIPTION = 60;

/** Canonical category id → short type code ('OTHER' when unknown). */
export function deriveType(j) {
  const catId = (j && j.category && j.category.id) || 'other';
  return CATEGORY_TYPE[catId] || 'OTHER';
}

/**
 * remote/hybrid/onsite from location + title text. Hybrid wins when both
 * keywords appear ("San Francisco, hybrid remote" → hybrid).
 */
export function deriveRmt(j) {
  const hay = `${(j && j.location) || ''} ${(j && j.title) || ''}`.toLowerCase();
  if (/\bhybrid\b/.test(hay)) return 'hybrid';
  if (/\bremote\b/.test(hay)) return 'remote';
  return 'onsite';
}

/** `comp` {min,max} in dollars → [low, high] in thousands, or [null, null]. */
export function compTuple(j) {
  const c = j && j.comp;
  if (!c || c.min == null || c.max == null) return [null, null];
  return [Math.round(c.min / 1000), Math.round(c.max / 1000)];
}

/** Lower-cased text the search box matches against, built once per job. */
export function searchHaystack({ co, role, loc }) {
  return `${co} ${role} ${loc}`.toLowerCase();
}

function visaNoteOf(flags) {
  if (flags.us_citizenship_required === true) return 'citizenship';
  if (flags.no_sponsorship === true) return 'no-sponsorship';
  return null;
}

/**
 * @param {RawJob} j
 * @param {number} [now]
 * @returns {Job}
 */
export function mapJob(j, now = Date.now()) {
  const raw = j || {};
  const tier = raw.company_tier && raw.company_tier.tier;
  const visaNote = visaNoteOf(raw.flags || {});
  const ts = parseTimestamp(raw.posted_at);
  const jobId = typeof raw.job_id === 'string' ? raw.job_id : '';
  const base = {
    id: jobId || (raw.id != null ? String(raw.id) : ''),
    co: raw.company || '—',
    role: raw.title || '—',
    loc: raw.location || '—',
    url: safeHttpUrl(raw.url),
    rmt: deriveRmt(raw),
    visa: visaNote === null,
    visaNote,
    tier: TIER_ORDER.includes(tier) ? tier : 'other',
    comp: compTuple(raw),
    type: deriveType(raw),
    posted: ageString(raw.posted_at, now),
    postedTs: Number.isNaN(ts) ? 0 : ts,
    jobId,
    desc: (typeof raw.description === 'string' && raw.description.length > MIN_REAL_DESCRIPTION)
      ? raw.description
      : '',
    closed: raw.is_closed === true,
  };
  return { ...base, hay: searchHaystack(base) };
}

/**
 * Ids can repeat (older payloads without job_id reuse slugs across sources).
 * Suffix repeats with `#n` so ids are unique React keys and selection targets.
 * @param {Job[]} jobs
 * @returns {Job[]}
 */
export function dedupeIds(jobs) {
  const seen = new Map();
  return jobs.map((j) => {
    const n = (seen.get(j.id) || 0) + 1;
    seen.set(j.id, n);
    return n === 1 ? j : { ...j, id: `${j.id}#${n}` };
  });
}

/**
 * Validate + map a fetched jobs payload.
 * @param {unknown} payload
 * @param {number} [now]
 * @returns {{ jobs: Job[], meta: JobsMeta }}
 */
export function normalizeJobsPayload(payload, now = Date.now()) {
  if (!payload || typeof payload !== 'object' || !Array.isArray(payload.jobs)) {
    throw new Error('jobs payload has no "jobs" array');
  }
  const meta = payload.meta && typeof payload.meta === 'object' ? payload.meta : {};
  return { jobs: dedupeIds(payload.jobs.map((j) => mapJob(j, now))), meta };
}
