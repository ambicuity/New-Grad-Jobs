// Sorting + keyboard selection for the hiring list. Pure: inputs are never mutated.

/** Sort keys in the order F2 cycles through them. The feed has no deadlines. */
export const SORT_KEYS = ['posted', 'comp', 'co'];

/** Direction a key starts in when first chosen: newest, highest pay, A→Z. */
const NATURAL_DIR = { posted: -1, comp: -1, co: 1 };

export const DEFAULT_SORT = Object.freeze({ key: 'posted', dir: -1 });

// Value extractors; null means "unknown" and always sorts last.
const VALUE = {
  posted: (j) => (j.postedTs > 0 ? j.postedTs : null),
  comp: (j) => (j.comp && j.comp[1] != null ? j.comp[1] : null),
  co: (j) => j.co,
};

const collator = new Intl.Collator(undefined, { sensitivity: 'base' });
const compareValues = (a, b) => (typeof a === 'string' ? collator.compare(a, b) : a - b);
const compareIds = (a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);

/**
 * Sorted copy of `jobs`. `dir` 1 = ascending (▲), -1 = descending (▼).
 * Missing values (no salary, unknown date) sort last in both directions;
 * ties break on the stable job id. Unknown keys keep the input order.
 * @param {import('./jobs.js').Job[]} jobs
 * @param {string} key
 * @param {1|-1} dir
 */
export function sortJobs(jobs, key, dir) {
  const value = VALUE[key];
  if (!value) return jobs.slice();
  const keyed = jobs.map((j) => ({ j, v: value(j) }));
  keyed.sort((a, b) => {
    if (a.v === null || b.v === null) {
      if (a.v !== b.v) return a.v === null ? 1 : -1;
      return compareIds(a.j, b.j);
    }
    return dir * compareValues(a.v, b.v) || compareIds(a.j, b.j);
  });
  return keyed.map(({ j }) => j);
}

/** Next key in the F2 cycle. */
export function nextSortKey(key) {
  return SORT_KEYS[(SORT_KEYS.indexOf(key) + 1) % SORT_KEYS.length];
}

/** Hiring header click: same key flips direction, a new key starts in its natural direction. */
export function clickJobSort({ key, dir }, clicked) {
  return key === clicked ? { key, dir: -dir } : { key: clicked, dir: NATURAL_DIR[clicked] || 1 };
}

/** Contributors header click: same key flips direction, a new key starts at 1. */
export function clickSort({ key, dir }, clicked) {
  return key === clicked ? { key, dir: -dir } : { key: clicked, dir: 1 };
}

/**
 * id of the row `delta` steps from `selectedId` (j/k, ↑/↓), or `selectedId`
 * unchanged at either end / when it isn't in the list.
 * @param {{id: string}[]} list
 * @param {string|null} selectedId
 * @param {number} delta
 */
export function stepSelection(list, selectedId, delta) {
  const idx = list.findIndex((j) => j.id === selectedId);
  if (idx === -1) return selectedId;
  const next = idx + delta;
  if (next < 0 || next >= list.length) return selectedId;
  return list[next].id;
}

/**
 * Keep the selection valid: if the selected id is no longer in `visible`,
 * fall back to the first visible row (or keep it when nothing is visible).
 */
export function reconcileSelection(visible, selectedId) {
  if (visible.some((j) => j.id === selectedId)) return selectedId;
  return visible[0] ? visible[0].id : selectedId;
}
