// The shareable view state (tab, search, filters, sort, selected job) lives
// in the query string so a link, a reload or the back button restores it.
// Parsing is defensive: anything unknown or oversized is dropped, never trusted.

import { EMPTY_FILTERS } from './filters.js';
import { DEFAULT_SORT, SORT_KEYS } from './sort.js';
import { RMT_ORDER, TIER_ORDER, TYPE_ORDER } from './taxonomy.js';
import { COUNTRY_CODES } from './location.js';
import { NEAR_MISS_REASONS } from './near-miss.js';
import { MAX_SIGNAL_LENGTH, MAX_SIGNAL_WORDS, TIER_KEYS, cleanWords } from './explore.js';

export const TAB_IDS = ['hiring', 'contributors', 'explore'];
const MAX_QUERY = 200;
const MAX_VALUE = 200;
const MAX_COMPANIES = 50;
const MAX_METROS = 20;

const P = {
  tab: 'tab', q: 'q', type: 'role', rmt: 'remote', tier: 'tier', company: 'co',
  visa: 'visa', sort: 'sort', job: 'job', saved: 'saved', newHours: 'new', metro: 'metro', country: 'country',
  include: 'include',
  // EXPLORE tab: include words, exclude words, tiers, query.
  xInclude: 'xi', xExclude: 'xe', xTier: 'xt', xQuery: 'xq',
};
// ?new=<hours>: roles first seen in the last N hours, for shareable "what's new" links. At most a week.
const MAX_NEW_HOURS = 168;

function readNewHours(value) {
  if (!/^\d{1,3}$/.test(value || '')) return null;
  const hours = Number(value);
  return hours >= 1 && hours <= MAX_NEW_HOURS ? hours : null;
}
const VISA_PARAM = { none: true, restricted: false };

/**
 * @typedef {object} ViewState
 * @property {'hiring'|'contributors'} tab
 * @property {string} q
 * @property {import('./filters.js').JobFilters} filters
 * @property {{key: string, dir: 1|-1}} sort
 * @property {string|null} job        Selected job id (the stable job_id).
 * @property {boolean} savedOnly
 * @property {{include: string[], exclude: string[], tiers: Set<string>, q: string}} explore  EXPLORE tab state.
 */

/** @returns {{include: string[], exclude: string[], tiers: Set<string>, q: string}} */
export function EMPTY_EXPLORE() {
  return { include: [], exclude: [], tiers: new Set(), q: '' };
}

/** @returns {ViewState} */
export function defaultView() {
  return { tab: 'hiring', q: '', filters: EMPTY_FILTERS(), sort: { ...DEFAULT_SORT }, job: null, savedOnly: false, explore: EMPTY_EXPLORE() };
}

const shortString = (v) => typeof v === 'string' && v.length > 0 && v.length <= MAX_VALUE;
const allowed = (list) => (v) => list.includes(v);

function readSet(params, name, isValid, max = Infinity) {
  return new Set(params.getAll(name).filter(isValid).slice(0, max));
}

function readSort(value) {
  const m = /^([a-z]+)-(asc|desc)$/.exec(value || '');
  if (!m || !SORT_KEYS.includes(m[1])) return { ...DEFAULT_SORT };
  return { key: m[1], dir: m[2] === 'asc' ? 1 : -1 };
}

function readTab(params, hash) {
  const explicit = params.get(P.tab);
  if (explicit !== null) return TAB_IDS.includes(explicit) ? explicit : 'hiring';
  // Legacy links: the pre-URL-state site used #contributors / #hiring.
  const legacy = (hash || '').replace(/^#/, '');
  return TAB_IDS.includes(legacy) ? legacy : 'hiring';
}

/**
 * @param {string|undefined} search  location.search
 * @param {string} [hash]            location.hash (legacy tab links)
 * @returns {ViewState}
 */
export function parseViewState(search, hash = '') {
  const params = new URLSearchParams(search || '');
  const job = params.get(P.job);
  const visa = params.get(P.visa);
  return {
    tab: readTab(params, hash),
    q: (params.get(P.q) || '').slice(0, MAX_QUERY),
    filters: {
      type: readSet(params, P.type, allowed(TYPE_ORDER)),
      rmt: readSet(params, P.rmt, allowed(RMT_ORDER)),
      tier: readSet(params, P.tier, allowed(TIER_ORDER)),
      company: readSet(params, P.company, shortString, MAX_COMPANIES),
      metro: readSet(params, P.metro, shortString, MAX_METROS),
      country: readSet(params, P.country, allowed(COUNTRY_CODES)),
      include: readSet(params, P.include, allowed(NEAR_MISS_REASONS)),
      visa: Object.hasOwn(VISA_PARAM, visa) ? VISA_PARAM[visa] : null,
      newWithinHours: readNewHours(params.get(P.newHours)),
    },
    sort: readSort(params.get(P.sort)),
    job: shortString(job) ? job : null,
    savedOnly: params.get(P.saved) === '1',
    explore: {
      include: cleanWords(params.getAll(P.xInclude).slice(0, MAX_SIGNAL_WORDS)),
      exclude: cleanWords(params.getAll(P.xExclude).slice(0, MAX_SIGNAL_WORDS)),
      tiers: readSet(params, P.xTier, allowed(TIER_KEYS)),
      q: (params.get(P.xQuery) || '').slice(0, MAX_QUERY),
    },
  };
}

/**
 * Query string for `view` ('' for the default view). Params this module does
 * not own (utm tags etc.) are carried over from `baseSearch`.
 * @param {ViewState} view
 * @param {string} [baseSearch]
 */
export function serializeViewState(view, baseSearch = '') {
  const params = new URLSearchParams(baseSearch);
  Object.values(P).forEach((name) => params.delete(name));
  const { filters, sort } = view;
  if (view.tab !== 'hiring') params.set(P.tab, view.tab);
  if (view.q) params.set(P.q, view.q);
  filters.type.forEach((v) => params.append(P.type, v));
  filters.rmt.forEach((v) => params.append(P.rmt, v));
  filters.tier.forEach((v) => params.append(P.tier, v));
  filters.company.forEach((v) => params.append(P.company, v));
  filters.metro.forEach((v) => params.append(P.metro, v));
  filters.country.forEach((v) => params.append(P.country, v));
  filters.include.forEach((v) => params.append(P.include, v));
  if (filters.visa !== null) params.set(P.visa, filters.visa ? 'none' : 'restricted');
  if (filters.newWithinHours) params.set(P.newHours, String(filters.newWithinHours));
  if (sort.key !== DEFAULT_SORT.key || sort.dir !== DEFAULT_SORT.dir) {
    params.set(P.sort, `${sort.key}-${sort.dir > 0 ? 'asc' : 'desc'}`);
  }
  if (view.job) params.set(P.job, view.job);
  if (view.savedOnly) params.set(P.saved, '1');
  const explore = view.explore || EMPTY_EXPLORE();
  explore.include.forEach((w) => params.append(P.xInclude, w.slice(0, MAX_SIGNAL_LENGTH)));
  explore.exclude.forEach((w) => params.append(P.xExclude, w.slice(0, MAX_SIGNAL_LENGTH)));
  explore.tiers.forEach((t) => params.append(P.xTier, t));
  if (explore.q) params.set(P.xQuery, explore.q);
  const out = params.toString();
  return out ? `?${out}` : '';
}

/** Two views are the same when they serialize identically. */
export function sameView(a, b) {
  return serializeViewState(a) === serializeViewState(b);
}
