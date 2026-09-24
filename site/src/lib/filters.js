// Hiring-view filtering. All functions are pure and never mutate their input:
// every "toggle" returns a new filters object with new Sets.

import { daysLeft } from './time.js';

/**
 * @typedef {object} JobFilters
 * @property {Set<string>} type
 * @property {Set<string>} rmt
 * @property {boolean|null} visa     true = sponsored only, false = US-only, null = any.
 * @property {Set<string>} cohort
 * @property {Set<string>} size
 * @property {Set<string>} company
 */

/**
 * The one place a filters object is built. Every facet the list filter reads
 * (including `company`) must be present, or `filters.<facet>.size` throws and
 * React unmounts the whole view — which is how Esc used to blank the page.
 * @returns {JobFilters}
 */
export function EMPTY_FILTERS() {
  return {
    type: new Set(), rmt: new Set(), visa: null, cohort: new Set(['26']), size: new Set(),
    company: new Set(),
  };
}

/** New Set with `val` added if absent, removed if present. */
export function toggleInSet(set, val) {
  const next = new Set(set);
  if (next.has(val)) next.delete(val);
  else next.add(val);
  return next;
}

/** Toggle one value of a Set-valued facet. */
export function toggleFacet(filters, key, val) {
  return { ...filters, [key]: toggleInSet(filters[key], val) };
}

/** Visa is tri-state: clicking the active value clears it back to null. */
export function toggleVisa(filters, val) {
  return { ...filters, visa: filters.visa === val ? null : val };
}

/** Number of user-set facets (cohort is a default, so it isn't counted). */
export function activeFilterCount(filters) {
  return filters.type.size + filters.rmt.size + (filters.visa !== null ? 1 : 0)
    + filters.size.size + filters.company.size;
}

/** Case-insensitive search over company, role, location and stack. */
export function matchesQuery(job, q) {
  if (!q) return true;
  const needle = q.toLowerCase();
  return `${job.co} ${job.role} ${job.loc} ${job.stack.join(' ')}`.toLowerCase().includes(needle);
}

/**
 * Apply every facet EXCEPT company. This feeds the HIRING NOW sidebar so the
 * company list doesn't collapse to the selected company — users can still
 * switch between companies after picking one.
 * @param {import('./jobs.js').Job[]} jobs
 * @param {{filters: JobFilters, q?: string, saved?: Set<string>, savedOnly?: boolean}} opts
 */
export function filterJobsExceptCompany(jobs, { filters, q = '', saved = new Set(), savedOnly = false }) {
  return jobs.filter((j) => {
    if (savedOnly && !saved.has(j.id)) return false;
    if (filters.type.size && !filters.type.has(j.type)) return false;
    if (filters.rmt.size && !filters.rmt.has(j.rmt)) return false;
    if (filters.visa !== null && j.visa !== filters.visa) return false;
    if (filters.cohort.size && !filters.cohort.has(j.cohort)) return false;
    if (filters.size.size && !filters.size.has(j.size)) return false;
    return matchesQuery(j, q);
  });
}

/** Narrow to the selected companies (no-op when none are selected). Returns a new array. */
export function filterByCompany(jobs, companies) {
  return companies.size ? jobs.filter((j) => companies.has(j.co)) : jobs.slice();
}

/** [company, count] pairs, most jobs first (stable for ties). */
export function companyCounts(jobs) {
  const m = new Map();
  jobs.forEach((j) => m.set(j.co, (m.get(j.co) || 0) + 1));
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

/** Histogram of days-to-deadline for the DEADLINE DIST. widget. */
export function deadlineBuckets(jobs, now = Date.now()) {
  const b = { w1: 0, w2: 0, m1: 0, m3: 0, m3p: 0 };
  jobs.forEach((j) => {
    const d = daysLeft(j.dl, now);
    if (d < 7) b.w1++;
    else if (d < 14) b.w2++;
    else if (d < 30) b.m1++;
    else if (d < 90) b.m3++;
    else b.m3p++;
  });
  return b;
}

/**
 * "NEW TODAY" stat. Kept byte-for-byte from the pre-Vite site for parity: it
 * matches single-digit hours, "1d" and "2d" (so "now" and 10-23h are missed).
 */
export function newTodayCount(jobs) {
  return jobs.filter((j) => /^\dh|^1d|^2d/.test(j.posted)).length;
}

/** Jobs whose (synthetic) deadline is under a week away. */
export function closingSoonCount(jobs, now = Date.now()) {
  return jobs.filter((j) => daysLeft(j.dl, now) < 7).length;
}
