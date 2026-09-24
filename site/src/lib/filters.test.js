import { describe, expect, it } from 'vitest';
import {
  EMPTY_FILTERS, activeFilterCount, companyCounts, filterByCompany, filterJobsExceptCompany,
  matchesQuery, toggleFacet, toggleInSet, toggleVisa,
} from './filters.js';
import { searchHaystack } from './jobs.js';

const job = (over) => {
  const j = {
    id: 'x', co: 'Acme', role: 'Software Engineer', loc: 'Austin, TX',
    type: 'SWE', rmt: 'onsite', visa: true, tier: 'other', ...over,
  };
  return { ...j, hay: searchHaystack(j) };
};

const JOBS = [
  job({ id: 'a', co: 'Acme', type: 'SWE', rmt: 'remote' }),
  job({ id: 'b', co: 'Beta', type: 'ML', visa: false, tier: 'faang_plus', loc: 'New York, NY' }),
  job({ id: 'c', co: 'Acme', type: 'ML', rmt: 'hybrid', role: 'ML Engineer' }),
  job({ id: 'd', co: 'Gamma', type: 'DATA', tier: 'unicorn' }),
];
const ids = (list) => list.map((j) => j.id);

describe('EMPTY_FILTERS', () => {
  it('returns a fresh object with every facet (incl. company) each call', () => {
    const a = EMPTY_FILTERS();
    const b = EMPTY_FILTERS();
    expect(a).not.toBe(b);
    expect(a.company).not.toBe(b.company);
    expect(Object.keys(a).sort()).toEqual(['company', 'rmt', 'tier', 'type', 'visa']);
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

  it('activeFilterCount counts every user-set facet', () => {
    let f = EMPTY_FILTERS();
    expect(activeFilterCount(f)).toBe(0);
    f = toggleVisa(toggleFacet(toggleFacet(f, 'type', 'ML'), 'company', 'Acme'), false);
    f = toggleFacet(f, 'tier', 'unicorn');
    expect(activeFilterCount(f)).toBe(4);
  });
});

describe('matchesQuery', () => {
  it('matches company, role and location case-insensitively', () => {
    expect(matchesQuery(JOBS[1], 'beta')).toBe(true);
    expect(matchesQuery(JOBS[2], 'ml eng')).toBe(true);
    expect(matchesQuery(JOBS[1], 'NEW YORK')).toBe(true);
    expect(matchesQuery(JOBS[0], 'zzz')).toBe(false);
    expect(matchesQuery(JOBS[0], '')).toBe(true);
    expect(matchesQuery(JOBS[0], '   ')).toBe(true);
  });

  it('requires every whitespace-separated term, in any order', () => {
    expect(matchesQuery(JOBS[2], 'engineer acme')).toBe(true);
    expect(matchesQuery(JOBS[2], 'engineer beta')).toBe(false);
  });

  it('builds the haystack on the fly for rows without one', () => {
    expect(matchesQuery({ co: 'Zed', role: 'R', loc: 'L' }, 'zed')).toBe(true);
  });
});

describe('filterJobsExceptCompany', () => {
  const run = (filters, extra = {}) => ids(filterJobsExceptCompany(JOBS, { filters, ...extra }));

  it('shows everything with no filters', () => {
    expect(run(EMPTY_FILTERS())).toEqual(['a', 'b', 'c', 'd']);
  });

  it('filters by type, remote, visa and tier', () => {
    expect(run(toggleFacet(EMPTY_FILTERS(), 'type', 'ML'))).toEqual(['b', 'c']);
    expect(run(toggleFacet(EMPTY_FILTERS(), 'rmt', 'hybrid'))).toEqual(['c']);
    expect(run(toggleVisa(EMPTY_FILTERS(), false))).toEqual(['b']);
    expect(run(toggleVisa(EMPTY_FILTERS(), true))).toEqual(['a', 'c', 'd']);
    expect(run(toggleFacet(EMPTY_FILTERS(), 'tier', 'faang_plus'))).toEqual(['b']);
  });

  it('applies the search query', () => {
    expect(run(EMPTY_FILTERS(), { q: 'acme' })).toEqual(['a', 'c']);
  });

  it('restricts to saved jobs in saved-only mode', () => {
    expect(run(EMPTY_FILTERS(), { saved: new Set(['c']), savedOnly: true })).toEqual(['c']);
    expect(run(EMPTY_FILTERS(), { saved: new Set(['c']), savedOnly: false })).toEqual(['a', 'b', 'c', 'd']);
  });

  it('ignores the company facet (HIRING NOW stays switchable)', () => {
    expect(run(toggleFacet(EMPTY_FILTERS(), 'company', 'Beta'))).toEqual(['a', 'b', 'c', 'd']);
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
