import { describe, expect, it } from 'vitest';
import { fmtComp, fmtK, pct, rowNumber } from './format.js';

describe('fmtComp', () => {
  it('formats a $k range', () => {
    expect(fmtComp([120, 180])).toBe('$120–180k');
    expect(fmtComp([120, 180], 'USD')).toBe('$120–180k');
  });

  it('labels every other currency instead of showing a dollar sign', () => {
    expect(fmtComp([62, 75], 'CAD')).toBe('CA$62–75k');
    expect(fmtComp([30, 40], 'GBP')).toBe('£30–40k');
    expect(fmtComp([45, 55], 'EUR')).toBe('€45–55k');
    expect(fmtComp([1200, 1800], 'INR')).toBe('₹12–18L');
    expect(fmtComp([350, 525], 'INR')).toBe('₹3.5–5.3L');
    expect(fmtComp([90, 110], 'AUD')).toBe('AUD 90–110k');
  });

  it.each([[[null, null]], [[120, null]], [null], [undefined], ['120']])('returns — for %j', (c) => {
    expect(fmtComp(c)).toBe('—');
  });
});

describe('pct', () => {
  it('rounds to a whole percentage', () => {
    expect(pct(1, 3)).toBe('33%');
    expect(pct(2, 3)).toBe('67%');
    expect(pct(5, 5)).toBe('100%');
  });

  it('returns — when the whole is zero', () => {
    expect(pct(0, 0)).toBe('—');
  });
});

describe('fmtK', () => {
  it.each([
    [0, '0'],
    [950, '950'],
    [1000, '1k'],
    [1234, '1.2k'],
    [12345, '12k'],
    [null, '—'],
    [undefined, '—'],
  ])('%j → %s', (n, s) => {
    expect(fmtK(n)).toBe(s);
  });
});

describe('rowNumber', () => {
  it('is 1-based and zero-padded to two digits', () => {
    expect(rowNumber(0)).toBe('01');
    expect(rowNumber(11)).toBe('12');
    expect(rowNumber(122)).toBe('123');
  });
});
