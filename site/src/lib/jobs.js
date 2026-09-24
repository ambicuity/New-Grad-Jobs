// Maps the scraper's published job records (jobs-index.json / jobs.json, see
// scripts/publish.py) to the row model the terminal views render.

import { CATEGORY_TYPE, TIER_SIZE } from './taxonomy.js';
import { addDays, ageString, parseTimestamp } from './time.js';

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
 * @property {{min?: number, max?: number, currency?: string}|null} [comp]
 */

/**
 * The row model rendered by the hiring view.
 * @typedef {object} Job
 * @property {string} id              Unique within the loaded list (duplicates get `#n`).
 * @property {string} co              Company.
 * @property {string} role            Title.
 * @property {string} loc             Location.
 * @property {string} url             Application URL ('' when absent).
 * @property {'remote'|'hybrid'|'onsite'} rmt
 * @property {boolean} visa           False when the posting rules out sponsorship.
 * @property {'S'|'M'|'L'|'XL'} size
 * @property {string[]} stack         Not in source data; ['—'].
 * @property {string} cohort          Always '26'.
 * @property {[number|null, number|null]} comp  Salary range in $k.
 * @property {string} dl              Synthetic deadline (posted + 90 days), YYYY-MM-DD.
 * @property {string} type            Short category code (SWE, ML, …).
 * @property {string} posted          Display age ("3h", "2d").
 * @property {number} postedTs        Epoch ms of posted_at (0 when unknown) — sort key.
 * @property {string} level
 * @property {string} jobId           `job_<hex>` or ''.
 * @property {string} desc            Description, or a one-line placeholder.
 */

/**
 * @typedef {object} JobsMeta
 * @property {string} [generated_at]
 * @property {number} [total_jobs]
 */

export const DEADLINE_WINDOW_DAYS = 90;
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

function placeholderDescription(j) {
  const where = j.location ? ` in ${j.location}` : '';
  return `${j.company || 'This company'} is hiring for ${j.title || 'this role'}${where}. Posted via ${j.source || 'their careers page'}.`;
}

/**
 * @param {RawJob} j
 * @param {number} [now]
 * @returns {Job}
 */
export function mapJob(j, now = Date.now()) {
  const raw = j || {};
  const tier = (raw.company_tier && raw.company_tier.tier) || 'other';
  const flags = raw.flags || {};
  const noSponsorship = flags.no_sponsorship === true || flags.us_citizenship_required === true;
  const ts = parseTimestamp(raw.posted_at);
  return {
    id: raw.id != null ? String(raw.id) : '',
    co: raw.company || '—',
    role: raw.title || '—',
    loc: raw.location || '—',
    url: raw.url || '',
    rmt: deriveRmt(raw),
    visa: !noSponsorship,
    size: TIER_SIZE[tier] || 'M',
    stack: ['—'],
    cohort: '26',
    comp: compTuple(raw),
    dl: addDays(raw.posted_at, DEADLINE_WINDOW_DAYS, now),
    type: deriveType(raw),
    posted: ageString(raw.posted_at, now),
    postedTs: Number.isNaN(ts) ? 0 : ts,
    level: 'entry',
    jobId: typeof raw.job_id === 'string' ? raw.job_id : '',
    desc: (typeof raw.description === 'string' && raw.description.length > MIN_REAL_DESCRIPTION)
      ? raw.description
      : placeholderDescription(raw),
  };
}

/**
 * The feed contains duplicate slugs (same role on several sources). Suffix
 * repeats with `#n` so ids are unique React keys and selection targets.
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
