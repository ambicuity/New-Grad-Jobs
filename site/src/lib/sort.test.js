import { describe, expect, it } from 'vitest';
import {
  SORT_KEYS, clickSort, nextSortKey, reconcileSelection, sortJobs, stepSelection,
} from './sort.js';

const NOW = Date.parse('2026-09-24T00:00:00Z');
const JOBS = [
  { id: 'a', co: 'beta', comp: [100, 150], postedTs: 3, dl: '2026-10-10' },
  { id: 'b', co: 'Alpha', comp: [null, null], postedTs: 9, dl: '2026-09-30' },
  { id: 'c', co: 'gamma', comp: [120, 200], postedTs: 0, dl: '2026-12-01' },
];
const ids = (list) => list.map((j) => j.id);

describe('sortJobs', () => {
  it('posted: newest first; missing timestamps last', () => {
    expect(ids(sortJobs(JOBS, 'posted', 1, NOW))).toEqual(['b', 'a', 'c']);
    expect(ids(sortJobs(JOBS, 'posted', -1, NOW))).toEqual(['c', 'a', 'b']);
  });

  it('deadline: soonest first', () => {
    expect(ids(sortJobs(JOBS, 'deadline', 1, NOW))).toEqual(['b', 'a', 'c']);
    expect(ids(sortJobs(JOBS, 'deadline', -1, NOW))).toEqual(['c', 'a', 'b']);
  });

  it('comp: highest top of range first; undisclosed sorts as 0', () => {
    expect(ids(sortJobs(JOBS, 'comp', 1, NOW))).toEqual(['c', 'a', 'b']);
    expect(ids(sortJobs(JOBS, 'comp', -1, NOW))).toEqual(['b', 'a', 'c']);
  });

  it('co: locale-aware A→Z', () => {
    expect(ids(sortJobs(JOBS, 'co', 1, NOW))).toEqual(['b', 'a', 'c']);
    expect(ids(sortJobs(JOBS, 'co', -1, NOW))).toEqual(['c', 'a', 'b']);
  });

  it('keeps input order for unknown keys and never mutates the input', () => {
    const before = ids(JOBS);
    expect(ids(sortJobs(JOBS, 'nope', 1, NOW))).toEqual(before);
    sortJobs(JOBS, 'co', 1, NOW);
    expect(ids(JOBS)).toEqual(before);
  });

  it('defaults now to the wall clock', () => {
    expect(sortJobs(JOBS, 'deadline', 1)).toHaveLength(3);
  });
});

describe('sort key helpers', () => {
  it('nextSortKey cycles posted → deadline → comp → co → posted', () => {
    expect(SORT_KEYS.map(nextSortKey)).toEqual(['deadline', 'comp', 'co', 'posted']);
  });

  it('clickSort flips direction on the same key, resets on a new key', () => {
    expect(clickSort({ key: 'co', dir: 1 }, 'co')).toEqual({ key: 'co', dir: -1 });
    expect(clickSort({ key: 'co', dir: -1 }, 'comp')).toEqual({ key: 'comp', dir: 1 });
  });
});

describe('selection helpers', () => {
  const list = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];

  it('stepSelection moves within bounds (j/k)', () => {
    expect(stepSelection(list, 'a', 1)).toBe('b');
    expect(stepSelection(list, 'b', -1)).toBe('a');
    expect(stepSelection(list, 'c', 1)).toBe('c');
    expect(stepSelection(list, 'a', -1)).toBe('a');
  });

  it('stepSelection is a no-op for ids not in the list or empty lists', () => {
    expect(stepSelection(list, 'zzz', 1)).toBe('zzz');
    expect(stepSelection([], null, 1)).toBeNull();
  });

  it('reconcileSelection keeps a visible id, else falls back to the first row', () => {
    expect(reconcileSelection(list, 'b')).toBe('b');
    expect(reconcileSelection(list, 'zzz')).toBe('a');
    expect(reconcileSelection([], 'zzz')).toBe('zzz');
    expect(reconcileSelection([], null)).toBeNull();
  });
});
