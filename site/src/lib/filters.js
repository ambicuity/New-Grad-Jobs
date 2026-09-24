// Hiring-view filtering. All functions are pure and never mutate their input:
// every "toggle" returns a new filters object with new Sets.

import { searchHaystack } from './jobs.js';

/**
 * @typedef {object} JobFilters
 * @property {Set<string>} type
 * @property {Set<string>} rmt
 * @property {boolean|null} visa     true = no restriction stated, false = restriction stated, null = any.
 * @property {Set<string>} tier
 * @property {Set<string>} company
 */

/**
 * The one place a filters object is built. Every facet the list filter reads
 * (including `company`) must be present, or `filters.<facet>.size` throws and
 * React unmounts the whole view — which is how Esc used to blank the page.
 * @returns {JobFilters}
 */
export function EMPTY_FILTERS() {
  return { type: new Set(), rmt: new Set(), visa: null, tier: new Set(), company: new Set() };
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

/** Number of user-set facets. */
export function activeFilterCount(filters) {
  return filters.type.size + filters.rmt.size + (filters.visa !== null ? 1 : 0)
    + filters.tier.size + filters.company.size;
}

/**
 * Case-insensitive search over company, role and location: every
 * whitespace-separated term must appear (in any order).
 */
export function matchesQuery(job, q) {
  const terms = (q || '').toLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return true;
  const hay = job.hay || searchHaystack(job);
  return terms.every((t) => hay.includes(t));
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
    if (filters.tier.size && !filters.tier.has(j.tier)) return false;
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
