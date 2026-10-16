import { describe, expect, it } from 'vitest';
import {
  DEFAULT_SORT, SORT_KEYS, clickJobSort, clickSort, nextSortKey, reconcileSelection, sortJobs,
  stepSelection,
} from './sort.js';

const JOBS = [
  { id: 'a', co: 'beta', comp: [100, 150], compCur: 'USD', postedTs: 3 },
  { id: 'b', co: 'Alpha', comp: [null, null], compCur: null, postedTs: 9 },
  { id: 'c', co: 'gamma', comp: [120, 200], compCur: 'USD', postedTs: 0 },
  { id: 'd', co: 'beta', comp: [90, 150], compCur: 'USD', postedTs: 3 },
];
const ids = (list) => list.map((j) => j.id);

describe('sortJobs (dir 1 = ascending, -1 = descending)', () => {
  it('posted: descending is newest first; unknown dates always last', () => {
    expect(ids(sortJobs(JOBS, 'posted', -1))).toEqual(['b', 'a', 'd', 'c']);
    expect(ids(sortJobs(JOBS, 'posted', 1))).toEqual(['a', 'd', 'b', 'c']);
  });

  it('comp: by top of range; undisclosed pay always last, whatever the direction', () => {
    expect(ids(sortJobs(JOBS, 'comp', -1))).toEqual(['c', 'a', 'd', 'b']);
    expect(ids(sortJobs(JOBS, 'comp', 1))).toEqual(['a', 'd', 'c', 'b']);
  });

  it('comp: compares pay only within one currency — US dollars first, then each other currency, then undisclosed', () => {
    const mixed = [
      { id: 'u1', comp: [100, 150], compCur: 'USD' },
      { id: 'c1', comp: [200, 300], compCur: 'CAD' },
      { id: 'i1', comp: [1200, 1800], compCur: 'INR' },
      { id: 'u2', comp: [120, 200], compCur: 'USD' },
      { id: 'c2', comp: [60, 70], compCur: 'CAD' },
      { id: 'n', comp: [null, null], compCur: null },
    ];
    expect(ids(sortJobs(mixed, 'comp', -1))).toEqual(['u2', 'u1', 'c1', 'c2', 'i1', 'n']);
    expect(ids(sortJobs(mixed, 'comp', 1))).toEqual(['u1', 'u2', 'c2', 'c1', 'i1', 'n']);
  });

  it('co: locale-aware, case-insensitive A→Z ascending', () => {
    expect(ids(sortJobs(JOBS, 'co', 1))).toEqual(['b', 'a', 'd', 'c']);
    expect(ids(sortJobs(JOBS, 'co', -1))).toEqual(['c', 'a', 'd', 'b']);
  });

  it('breaks ties by id (ascending) regardless of direction', () => {
    // a and d tie on company, posted and comp-high.
    for (const key of SORT_KEYS) {
      for (const dir of [1, -1]) {
        const out = ids(sortJobs(JOBS, key, dir));
        expect(out.indexOf('a')).toBeLessThan(out.indexOf('d'));
      }
    }
  });

  it('keeps input order for unknown keys and never mutates the input', () => {
    const before = ids(JOBS);
    expect(ids(sortJobs(JOBS, 'deadline', 1))).toEqual(before);
    sortJobs(JOBS, 'co', 1);
    expect(ids(JOBS)).toEqual(before);
  });
});

describe('sort key helpers', () => {
  it('has no deadline sort (the feed has no deadlines)', () => {
    expect(SORT_KEYS).toEqual(['posted', 'comp', 'co']);
    expect(DEFAULT_SORT).toEqual({ key: 'posted', dir: -1 });
  });

  it('nextSortKey cycles posted → comp → co → posted', () => {
    expect(SORT_KEYS.map(nextSortKey)).toEqual(['comp', 'co', 'posted']);
  });

  it('clickJobSort flips on the same key and starts a new key in its natural direction', () => {
    expect(clickJobSort({ key: 'co', dir: 1 }, 'co')).toEqual({ key: 'co', dir: -1 });
    expect(clickJobSort({ key: 'co', dir: -1 }, 'comp')).toEqual({ key: 'comp', dir: -1 });
    expect(clickJobSort({ key: 'comp', dir: -1 }, 'posted')).toEqual({ key: 'posted', dir: -1 });
    expect(clickJobSort({ key: 'posted', dir: -1 }, 'co')).toEqual({ key: 'co', dir: 1 });
  });

  it('clickSort (contributors) flips on the same key, resets to 1 on a new key', () => {
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
