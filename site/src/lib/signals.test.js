// Parity with the scraper's matcher is the whole point: every expectation here
// that reads the fixture was produced by scripts/ngj/filters.py.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  TRACK_SUFFIX, compileExclusions, compileSignalSet, compileSignals, isTitleExcluded, matchesAny, signalPattern,
} from './signals.js';

const fixture = JSON.parse(readFileSync(join(process.cwd(), 'test', 'fixtures', 'signal-parity.json'), 'utf8'));

describe('parity with ngj.filters (generated fixture)', () => {
  it('has_new_grad_signal: whole tokens, level tokens, bare years', () => {
    fixture.titles.forEach((title, ti) => {
      fixture.signals.forEach((signal, si) => {
        const got = matchesAny(title, compileSignals([signal]));
        expect(got, `new_grad(${JSON.stringify(title)}, ${JSON.stringify(signal)})`).toBe(fixture.new_grad[ti][si]);
      });
    });
  });

  it('has_track_signal: whole words plus inflections', () => {
    fixture.titles.forEach((title, ti) => {
      fixture.signals.forEach((signal, si) => {
        const got = matchesAny(title, compileSignals([signal], TRACK_SUFFIX));
        expect(got, `track(${JSON.stringify(title)}, ${JSON.stringify(signal)})`).toBe(fixture.track[ti][si]);
      });
    });
  });

  it('is_title_excluded: alphanumeric edges, plural s, intern inflections', () => {
    fixture.titles.forEach((title, ti) => {
      fixture.exclusions.forEach((word, ei) => {
        const got = isTitleExcluded(title, compileExclusions([word]));
        expect(got, `excluded(${JSON.stringify(title)}, ${JSON.stringify(word)})`).toBe(fixture.excluded[ti][ei]);
      });
    });
  });
});

describe('signalPattern / compile helpers', () => {
  it('returns null for blank or non-string input', () => {
    expect(signalPattern('   ')).toBeNull();
    expect(compileSignals([])).toBeNull();
    expect(compileSignals(['', null, 3])).toBeNull();
    expect(compileExclusions(['  '])).toBeNull();
    expect(matchesAny('x', null)).toBe(false);
    expect(matchesAny(42, compileSignals(['x']))).toBe(false);
  });

  it('compileSignalSet keeps a title matching any include word and no exclude word', () => {
    const set = compileSignalSet({ include: ['rust', 'c++', 'new grad'], exclude: ['senior', 'intern'] });
    expect(set.test('Rust Engineer')).toBe(true);
    expect(set.test('C++ Developer, New Grad')).toBe(true);
    expect(set.test('Senior Rust Engineer')).toBe(false);
    expect(set.test('Rust Intern')).toBe(false);
    expect(set.test('Trustworthy AI Lead')).toBe(false); // "rust" inside "Trustworthy" never matches
    expect(compileSignalSet({}).test('anything')).toBe(true);
    expect(compileSignalSet({ exclude: ['senior'] }).test('Senior Anything')).toBe(false);
    expect(compileSignalSet({ exclude: ['manager'] }).test('Associate Product Manager')).toBe(true);
    expect(isTitleExcluded('', compileExclusions(['x']))).toBe(false);
  });
});
