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
 * @property {Set<string>} metro    "City, ST" labels (lib/location.js metroOf).
 * @property {Set<string>} country  ISO codes: US, CA, IN.
 * @property {number|null} newWithinHours  Only roles first seen in the last N hours (the ?new= link); null = any.
 */

/**
 * The one place a filters object is built. Every facet the list filter reads
 * (including `company`) must be present, or `filters.<facet>.size` throws and
 * React unmounts the whole view — which is how Esc used to blank the page.
 * @returns {JobFilters}
 */
export function EMPTY_FILTERS() {
  return {
    type: new Set(), rmt: new Set(), visa: null, tier: new Set(), company: new Set(),
    metro: new Set(), country: new Set(), newWithinHours: null,
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

/** Drops the new-roles window, keeping every other facet. */
export function clearNewWindow(filters) {
  return { ...filters, newWithinHours: null };
}

/** Number of user-set facets. */
export function activeFilterCount(filters) {
  return filters.type.size + filters.rmt.size + (filters.visa !== null ? 1 : 0)
    + filters.tier.size + filters.company.size + filters.metro.size + filters.country.size
    + (filters.newWithinHours ? 1 : 0);
}

const HOUR_MS = 3600e3;

/** True when the role was first seen within `hours` of `now` (a role with no first-seen time never is). */
function seenWithin(job, hours, now) {
  return job.firstSeenTs !== null && job.firstSeenTs !== undefined && now - job.firstSeenTs <= hours * HOUR_MS;
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
 * @param {{filters: JobFilters, q?: string, saved?: Set<string>, savedOnly?: boolean, now?: number}} opts
 *   `now` anchors the new-roles window; the dashboard passes the feed's generation time.
 */
export function filterJobsExceptCompany(jobs, opts) {
  return filterJobsExcept(jobs, opts, COMPANY_ONLY);
}

const COMPANY_ONLY = new Set(['company']);

/**
 * Apply every facet except the ones named in `ignore` (always excluding
 * `company`, which filterByCompany applies last). A facet's own list needs
 * counts computed without that facet, so the list stays switchable.
 * @param {Set<string>} ignore  facet names: 'metro', 'country', ...
 */
export function filterJobsExcept(jobs, { filters, q = '', saved = new Set(), savedOnly = false, now = Date.now() }, ignore = COMPANY_ONLY) {
  const skip = (name) => ignore.has(name);
  return jobs.filter((j) => {
    if (savedOnly && !saved.has(j.id)) return false;
    if (filters.type.size && !filters.type.has(j.type)) return false;
    if (filters.rmt.size && !filters.rmt.has(j.rmt)) return false;
    if (filters.visa !== null && j.visa !== filters.visa) return false;
    if (filters.tier.size && !filters.tier.has(j.tier)) return false;
    if (!skip('metro') && filters.metro.size && !filters.metro.has(j.metro)) return false;
    if (!skip('country') && filters.country.size && !filters.country.has(j.country)) return false;
    if (filters.newWithinHours && !seenWithin(j, filters.newWithinHours, now)) return false;
    return matchesQuery(j, q);
  });
}

/** Narrow to the selected companies (no-op when none are selected). Returns a new array. */
export function filterByCompany(jobs, companies) {
  return companies.size ? jobs.filter((j) => companies.has(j.co)) : jobs.slice();
}

/** [company, count] pairs, most jobs first (stable for ties). */
export function companyCounts(jobs) {
  return countBy(jobs, (j) => j.co);
}

/** [metro, count] pairs, most jobs first; jobs without a recognisable metro are left out. */
export function metroCounts(jobs) {
  return countBy(jobs, (j) => j.metro);
}

/** [countryCode, count] pairs, most jobs first. */
export function countryCounts(jobs) {
  return countBy(jobs, (j) => j.country);
}

function countBy(jobs, key) {
  const m = new Map();
  jobs.forEach((j) => {
    const k = key(j);
    if (k) m.set(k, (m.get(k) || 0) + 1);
  });
  return [...m.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
}
