// Headline numbers for the hiring stats strip. Every figure is derived from
// the published feed — nothing here is estimated, projected or hard-coded.

import { pct } from './format.js';

export const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * Posted within the last 24 hours, from the posting timestamp. A timestamp
 * slightly in the future (scraper clock skew) counts as new.
 * @param {{postedTs: number}} job
 * @param {number} [now]
 */
export function isNewToday(job, now = Date.now()) {
  return job.postedTs > 0 && now - job.postedTs < DAY_MS;
}

/** Median of a list of numbers (null when empty). Never mutates the input. */
export function median(values) {
  if (!values.length) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

const compMidpoint = (j) => (j.comp && j.comp[0] != null && j.comp[1] != null
  ? (j.comp[0] + j.comp[1]) / 2
  : null);

/**
 * @typedef {object} FeedStats
 * @property {number} total      Every job in the feed.
 * @property {number} open       Jobs not marked closed.
 * @property {number} closed
 * @property {number} newToday   Open jobs posted in the last 24h.
 * @property {number} companies  Distinct companies with an open job.
 * @property {{median: number|null, n: number}} comp  Median midpoint of the disclosed pay ranges ($k), and how many open jobs disclose one.
 * @property {{n: number, pct: string}} visaClear     Open jobs whose posting states no visa/citizenship restriction.
 */

/**
 * @param {import('./jobs.js').Job[]} jobs
 * @param {number} [now]
 * @returns {FeedStats}
 */
export function computeStats(jobs, now = Date.now()) {
  const open = jobs.filter((j) => !j.closed);
  const mids = open.map(compMidpoint).filter((m) => m !== null);
  const med = median(mids);
  const visaClear = open.filter((j) => j.visa).length;
  return {
    total: jobs.length,
    open: open.length,
    closed: jobs.length - open.length,
    newToday: open.filter((j) => isNewToday(j, now)).length,
    companies: new Set(open.map((j) => j.co)).size,
    comp: { median: med === null ? null : Math.round(med), n: mids.length },
    visaClear: { n: visaClear, pct: pct(visaClear, open.length) },
  };
}
