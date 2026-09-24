import { describe, expect, it } from 'vitest';
import { contrastRatio, relativeLuminance } from './color.js';
import { BBG } from './theme.js';

const AA_TEXT = 4.5;

describe('contrast math (WCAG 2.x)', () => {
  it('matches the reference extremes', () => {
    expect(relativeLuminance('#000000')).toBe(0);
    expect(relativeLuminance('#ffffff')).toBeCloseTo(1, 5);
    expect(contrastRatio('#000', '#fff')).toBeCloseTo(21, 5);
    expect(contrastRatio('#ffffff', '#000000')).toBeCloseTo(21, 5);
  });

  it('matches a known mid-grey value', () => {
    // #767676 on white is the classic "just passes AA" grey (4.54:1).
    expect(contrastRatio('#767676', '#ffffff')).toBeCloseTo(4.54, 2);
  });

  it('rejects malformed colours', () => {
    expect(() => relativeLuminance('red')).toThrow(/hex colour/);
  });
});

describe('theme text contrast', () => {
  const backgrounds = { bg: BBG.bg, panel: BBG.panel, panel2: BBG.panel2, selBg: BBG.selBg };

  it.each(Object.entries(backgrounds))('dim text passes AA (4.5:1) on %s', (_name, bg) => {
    expect(contrastRatio(BBG.dim, bg)).toBeGreaterThanOrEqual(AA_TEXT);
  });

  it.each(Object.entries(backgrounds))('placeholder text passes AA (4.5:1) on %s', (_name, bg) => {
    expect(contrastRatio(BBG.placeholder, bg)).toBeGreaterThanOrEqual(AA_TEXT);
  });

  it.each(['ink', 'acc', 'acc2', 'ok', 'hot', 'warn'])('%s passes AA on black', (k) => {
    expect(contrastRatio(BBG[k], BBG.bg)).toBeGreaterThanOrEqual(AA_TEXT);
  });

  it('black text on the amber accent passes AA', () => {
    expect(contrastRatio('#000000', BBG.acc)).toBeGreaterThanOrEqual(AA_TEXT);
  });
});
