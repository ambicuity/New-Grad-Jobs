import { describe, expect, it } from 'vitest';
import {
  addDays, ageString, daysLeft, deadlineHot, deadlineLabel, formatAgo, parseTimestamp,
} from './time.js';

const NOW = Date.parse('2026-09-24T16:00:00Z');
const HOUR = 3600000;
const DAY = 24 * HOUR;

describe('parseTimestamp', () => {
  it('parses Z-suffixed UTC timestamps', () => {
    expect(parseTimestamp('2026-09-24T14:50:21Z')).toBe(Date.UTC(2026, 8, 24, 14, 50, 21));
  });

  it('parses offset timestamps', () => {
    expect(parseTimestamp('2026-09-24T15:37:03.315021+00:00')).toBe(Date.UTC(2026, 8, 24, 15, 37, 3, 315));
  });

  it('reads zone-less timestamps as UTC (scraper output), incl. microseconds', () => {
    expect(parseTimestamp('2026-09-24T14:50:21.850000')).toBe(Date.UTC(2026, 8, 24, 14, 50, 21, 850));
    expect(parseTimestamp('2026-09-24T14:50')).toBe(Date.UTC(2026, 8, 24, 14, 50));
  });

  it('parses plain dates as UTC midnight', () => {
    expect(parseTimestamp('2026-12-23')).toBe(Date.UTC(2026, 11, 23));
  });

  it.each([null, undefined, '', 'garbage', 42])('returns NaN for %j', (v) => {
    expect(parseTimestamp(v)).toBeNaN();
  });
});

describe('ageString', () => {
  it.each([
    ['2026-09-24T14:50:21Z', '1h'],
    ['2026-09-24T15:30:00Z', 'now'],
    ['2026-09-24T04:00:00Z', '12h'],
    ['2026-09-23T15:00:00Z', '1d'],
    ['2026-09-20T16:00:00Z', '4d'],
    ['2026-09-10T16:00:00Z', '2w'],
    ['2026-07-01T16:00:00Z', '2mo'],
  ])('%s → %s', (iso, expected) => {
    expect(ageString(iso, NOW)).toBe(expected);
  });

  it('handles zone-less UTC timestamps the same as Z-suffixed ones', () => {
    expect(ageString('2026-09-24T14:50:21.850000', NOW)).toBe(ageString('2026-09-24T14:50:21.850Z', NOW));
  });

  it('treats future timestamps as now', () => {
    expect(ageString('2026-09-25T00:00:00Z', NOW)).toBe('now');
  });

  it('returns an em dash for missing or unparseable input', () => {
    expect(ageString(null, NOW)).toBe('—');
    expect(ageString('', NOW)).toBe('—');
    expect(ageString('not a date', NOW)).toBe('—');
  });

  it('defaults now to the wall clock', () => {
    expect(ageString(new Date().toISOString())).toBe('now');
  });
});

describe('addDays', () => {
  it('adds whole days to a timestamp and returns YYYY-MM-DD', () => {
    expect(addDays('2026-09-24T14:50:21Z', 90, NOW)).toBe('2026-12-23');
  });

  it('uses now when the timestamp is missing or invalid', () => {
    expect(addDays(undefined, 1, NOW)).toBe('2026-09-25');
    expect(addDays('nope', 0, NOW)).toBe('2026-09-24');
  });
});

describe('daysLeft / deadlineLabel / deadlineHot', () => {
  const dl = (days) => new Date(NOW + days * DAY).toISOString();

  it('counts whole days to the deadline', () => {
    expect(daysLeft('2026-09-30', NOW)).toBe(5); // 5.33 days, rounded
    expect(daysLeft(dl(-3), NOW)).toBe(-3);
  });

  it('returns 999 when there is no (valid) deadline', () => {
    expect(daysLeft('', NOW)).toBe(999);
    expect(daysLeft(null, NOW)).toBe(999);
    expect(daysLeft('bogus', NOW)).toBe(999);
  });

  it.each([
    [-1, 'closed'],
    [0, 'today'],
    [5, '5d left'],
    [15, '2w left'],
    [65, '2mo left'],
  ])('%i days → %s', (days, label) => {
    expect(deadlineLabel(dl(days), NOW)).toBe(label);
  });

  it('is hot within two weeks', () => {
    expect(deadlineHot(dl(14), NOW)).toBe(true);
    expect(deadlineHot(dl(15), NOW)).toBe(false);
  });

  it('defaults now to the wall clock', () => {
    expect(daysLeft(new Date(Date.now() + 2 * DAY).toISOString())).toBe(2);
    expect(deadlineLabel(new Date(Date.now() + 2 * DAY).toISOString())).toBe('2d left');
    expect(deadlineHot(new Date(Date.now() + 2 * DAY).toISOString())).toBe(true);
  });
});

describe('formatAgo', () => {
  it.each([
    [30 * 1000, '30s'],
    [5 * 60 * 1000, '5m'],
    [3 * HOUR, '3h'],
    [2 * DAY, '2d'],
    [14 * DAY, '2w'],
    [90 * DAY, '3mo'],
    [800 * DAY, '2y'],
  ])('%i ms ago → %s', (ago, expected) => {
    expect(formatAgo(new Date(NOW - ago).toISOString(), NOW)).toBe(expected);
  });

  it('returns an em dash for missing dates', () => {
    expect(formatAgo(undefined, NOW)).toBe('—');
  });

  it('clamps future dates to 0s', () => {
    expect(formatAgo(new Date(NOW + DAY).toISOString(), NOW)).toBe('0s');
  });
});
