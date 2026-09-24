// Sorting + keyboard selection for the hiring list. Pure: inputs are never mutated.

import { daysLeft } from './time.js';

/** Sort keys in the order F2 cycles through them. */
export const SORT_KEYS = ['posted', 'deadline', 'comp', 'co'];

// Undisclosed comp sorts as 0 (legacy behaviour used `null - x`, which is the same).
const compHigh = (j) => (j.comp && j.comp[1] != null ? j.comp[1] : 0);

/**
 * Sorted copy of `jobs`. `dir` 1 is the natural order for each key (newest,
 * soonest deadline, highest comp, A→Z); -1 reverses it. Unknown keys keep the
 * input order.
 * @param {import('./jobs.js').Job[]} jobs
 * @param {string} key
 * @param {1|-1} dir
 * @param {number} [now]
 */
export function sortJobs(jobs, key, dir, now = Date.now()) {
  const out = jobs.slice();
  if (key === 'deadline') out.sort((a, b) => dir * (daysLeft(a.dl, now) - daysLeft(b.dl, now)));
  if (key === 'comp') out.sort((a, b) => dir * (compHigh(b) - compHigh(a)));
  if (key === 'co') out.sort((a, b) => dir * a.co.localeCompare(b.co));
  if (key === 'posted') out.sort((a, b) => dir * (b.postedTs - a.postedTs));
  return out;
}

/** Next key in the F2 cycle. */
export function nextSortKey(key) {
  return SORT_KEYS[(SORT_KEYS.indexOf(key) + 1) % SORT_KEYS.length];
}

/** Header click: same key flips direction, a new key starts ascending. */
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
