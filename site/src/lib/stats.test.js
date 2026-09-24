import { describe, expect, it } from 'vitest';
import { DAY_MS, computeStats, isNewToday, median } from './stats.js';

const NOW = Date.parse('2026-09-24T16:00:00Z');
const HOUR = 3600000;
const job = (over) => ({
  id: 'x', co: 'Acme', postedTs: NOW - 2 * DAY_MS, comp: [null, null], visa: true, closed: false, ...over,
});

describe('isNewToday', () => {
  it('is true for postings under 24h old, from the timestamp (not the age string)', () => {
    expect(isNewToday(job({ postedTs: NOW - 10 * HOUR }), NOW)).toBe(true); // "10h" was missed by the old regex
    expect(isNewToday(job({ postedTs: NOW - 5 * 60000 }), NOW)).toBe(true); // "now"
    expect(isNewToday(job({ postedTs: NOW - DAY_MS + 1 }), NOW)).toBe(true);
  });

  it('is false at/after 24h and for unknown timestamps', () => {
    expect(isNewToday(job({ postedTs: NOW - DAY_MS }), NOW)).toBe(false);
    expect(isNewToday(job({ postedTs: NOW - 2 * DAY_MS }), NOW)).toBe(false);
    expect(isNewToday(job({ postedTs: 0 }), NOW)).toBe(false);
  });

  it('counts a slightly-future timestamp (clock skew) as new', () => {
    expect(isNewToday(job({ postedTs: NOW + HOUR }), NOW)).toBe(true);
  });

  it('defaults now to the wall clock', () => {
    expect(isNewToday(job({ postedTs: Date.now() - HOUR }))).toBe(true);
  });
});

describe('median', () => {
  it('handles odd, even and empty inputs without mutating', () => {
    const odd = [5, 1, 3];
    expect(median(odd)).toBe(3);
    expect(odd).toEqual([5, 1, 3]);
    expect(median([1, 2, 3, 4])).toBe(2.5);
    expect(median([])).toBeNull();
  });
});

describe('computeStats', () => {
  const JOBS = [
    job({ id: 'a', co: 'Acme', postedTs: NOW - HOUR, comp: [100, 140] }), // mid 120
    job({ id: 'b', co: 'Beta', postedTs: NOW - 12 * HOUR, comp: [150, 250], visa: false }), // mid 200
    job({ id: 'c', co: 'Acme', comp: [80, 100] }), // mid 90
    job({ id: 'd', co: 'Gamma' }),
    job({ id: 'e', co: 'Closed Co', postedTs: NOW - HOUR, comp: [900, 900], closed: true }),
  ];

  it('derives every number from the data and excludes closed jobs', () => {
    expect(computeStats(JOBS, NOW)).toEqual({
      total: 5,
      open: 4,
      closed: 1,
      newToday: 2,
      companies: 3,
      comp: { median: 120, n: 3 },
      visaClear: { n: 3, pct: '75%' },
    });
  });

  it('reports no median when no open job discloses pay', () => {
    const s = computeStats([job({ id: 'a' })], NOW);
    expect(s.comp).toEqual({ median: null, n: 0 });
  });

  it('copes with an empty feed', () => {
    expect(computeStats([], NOW)).toEqual({
      total: 0, open: 0, closed: 0, newToday: 0, companies: 0,
      comp: { median: null, n: 0 }, visaClear: { n: 0, pct: '—' },
    });
  });

  it('rounds the median midpoint to whole $k', () => {
    const s = computeStats([job({ id: 'a', comp: [100, 125] })], NOW); // 112.5
    expect(s.comp.median).toBe(113);
  });

  it('defaults now to the wall clock', () => {
    expect(computeStats([job({ postedTs: Date.now() - HOUR })]).newToday).toBe(1);
  });
});
