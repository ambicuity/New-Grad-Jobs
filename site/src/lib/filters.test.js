import { describe, expect, it } from 'vitest';
import {
  EMPTY_FILTERS, activeFilterCount, closingSoonCount, companyCounts, deadlineBuckets,
  filterByCompany, filterJobsExceptCompany, matchesQuery, newTodayCount, toggleFacet, toggleInSet,
  toggleVisa,
} from './filters.js';

const NOW = Date.parse('2026-09-24T00:00:00Z');
const inDays = (d) => new Date(NOW + d * 86400000).toISOString().slice(0, 10);

const job = (over) => ({
  id: 'x', co: 'Acme', role: 'Software Engineer', loc: 'Austin, TX', stack: ['—'],
  type: 'SWE', rmt: 'onsite', visa: true, cohort: '26', size: 'M', dl: inDays(60), posted: '3h',
  ...over,
});

const JOBS = [
  job({ id: 'a', co: 'Acme', type: 'SWE', rmt: 'remote' }),
  job({ id: 'b', co: 'Beta', type: 'ML', visa: false, size: 'XL', loc: 'New York, NY' }),
  job({ id: 'c', co: 'Acme', type: 'ML', rmt: 'hybrid', role: 'ML Engineer' }),
  job({ id: 'd', co: 'Gamma', type: 'DATA', cohort: '25' }),
];
const ids = (list) => list.map((j) => j.id);

describe('EMPTY_FILTERS', () => {
  it('returns a fresh object with every facet (incl. company) each call', () => {
    const a = EMPTY_FILTERS();
    const b = EMPTY_FILTERS();
    expect(a).not.toBe(b);
    expect(a.company).not.toBe(b.company);
    expect(Object.keys(a).sort()).toEqual(['cohort', 'company', 'rmt', 'size', 'type', 'visa']);
    expect([...a.cohort]).toEqual(['26']);
    expect(a.visa).toBeNull();
  });
});

describe('toggles are immutable', () => {
  it('toggleInSet adds then removes without mutating', () => {
    const s = new Set(['a']);
    const added = toggleInSet(s, 'b');
    expect([...added]).toEqual(['a', 'b']);
    expect([...toggleInSet(added, 'a')]).toEqual(['b']);
    expect([...s]).toEqual(['a']);
  });

  it('toggleFacet returns a new filters object', () => {
    const f = EMPTY_FILTERS();
    const next = toggleFacet(f, 'type', 'ML');
    expect(next).not.toBe(f);
    expect(next.type.has('ML')).toBe(true);
    expect(f.type.size).toBe(0);
  });

  it('toggleVisa is tri-state', () => {
    const f = EMPTY_FILTERS();
    const yes = toggleVisa(f, true);
    expect(yes.visa).toBe(true);
    expect(toggleVisa(yes, true).visa).toBeNull();
    expect(toggleVisa(yes, false).visa).toBe(false);
    expect(f.visa).toBeNull();
  });

  it('activeFilterCount ignores the default cohort', () => {
    let f = EMPTY_FILTERS();
    expect(activeFilterCount(f)).toBe(0);
    f = toggleVisa(toggleFacet(toggleFacet(f, 'type', 'ML'), 'company', 'Acme'), false);
    expect(activeFilterCount(f)).toBe(3);
  });
});

describe('matchesQuery', () => {
  it('matches company, role, location and stack case-insensitively', () => {
    expect(matchesQuery(JOBS[1], 'beta')).toBe(true);
    expect(matchesQuery(JOBS[2], 'ml eng')).toBe(true);
    expect(matchesQuery(JOBS[1], 'NEW YORK')).toBe(true);
    expect(matchesQuery(JOBS[0], 'zzz')).toBe(false);
    expect(matchesQuery(JOBS[0], '')).toBe(true);
  });
});

describe('filterJobsExceptCompany', () => {
  const run = (filters, extra = {}) => ids(filterJobsExceptCompany(JOBS, { filters, ...extra }));

  it('applies the default cohort filter', () => {
    expect(run(EMPTY_FILTERS())).toEqual(['a', 'b', 'c']);
  });

  it('filters by type, remote, visa and size', () => {
    expect(run(toggleFacet(EMPTY_FILTERS(), 'type', 'ML'))).toEqual(['b', 'c']);
    expect(run(toggleFacet(EMPTY_FILTERS(), 'rmt', 'hybrid'))).toEqual(['c']);
    expect(run(toggleVisa(EMPTY_FILTERS(), false))).toEqual(['b']);
    expect(run(toggleFacet(EMPTY_FILTERS(), 'size', 'XL'))).toEqual(['b']);
  });

  it('shows every cohort when the cohort facet is cleared', () => {
    expect(run(toggleFacet(EMPTY_FILTERS(), 'cohort', '26'))).toEqual(['a', 'b', 'c', 'd']);
  });

  it('applies the search query', () => {
    expect(run(EMPTY_FILTERS(), { q: 'acme' })).toEqual(['a', 'c']);
  });

  it('restricts to saved jobs in saved-only mode', () => {
    expect(run(EMPTY_FILTERS(), { saved: new Set(['c']), savedOnly: true })).toEqual(['c']);
    expect(run(EMPTY_FILTERS(), { saved: new Set(['c']), savedOnly: false })).toEqual(['a', 'b', 'c']);
  });

  it('ignores the company facet (HIRING NOW stays switchable)', () => {
    expect(run(toggleFacet(EMPTY_FILTERS(), 'company', 'Beta'))).toEqual(['a', 'b', 'c']);
  });
});

describe('company facet', () => {
  it('filterByCompany narrows to selected companies and copies otherwise', () => {
    expect(ids(filterByCompany(JOBS, new Set(['Acme'])))).toEqual(['a', 'c']);
    expect(ids(filterByCompany(JOBS, new Set(['Acme', 'Gamma'])))).toEqual(['a', 'c', 'd']);
    const all = filterByCompany(JOBS, new Set());
    expect(all).toEqual(JOBS);
    expect(all).not.toBe(JOBS);
  });

  it('companyCounts orders companies by job count', () => {
    expect(companyCounts(JOBS)).toEqual([['Acme', 2], ['Beta', 1], ['Gamma', 1]]);
    expect(companyCounts([])).toEqual([]);
  });
});

describe('stats helpers', () => {
  it('deadlineBuckets histograms days-to-deadline', () => {
    const list = [-2, 3, 10, 20, 45, 100, 200].map((d, i) => job({ id: String(i), dl: inDays(d) }));
    expect(deadlineBuckets(list, NOW)).toEqual({ w1: 2, w2: 1, m1: 1, m3: 1, m3p: 2 });
  });

  it('newTodayCount keeps the legacy regex: single-digit hours, 1d and 2d', () => {
    // Known quirk preserved from the pre-Vite site: 'now' and 10-23h are not counted.
    const list = ['now', '3h', '23h', '1d', '2d', '3d', '1w', '2mo'].map((posted, i) => job({ id: String(i), posted }));
    expect(newTodayCount(list)).toBe(3);
  });

  it('closingSoonCount counts deadlines under a week away', () => {
    const list = [-1, 6, 7, 30].map((d, i) => job({ id: String(i), dl: inDays(d) }));
    expect(closingSoonCount(list, NOW)).toBe(2);
  });
});
