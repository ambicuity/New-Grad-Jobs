import { describe, expect, it } from 'vitest';
import {
  NEAR_MISS_INFO, NEAR_MISS_REASONS, nearMissNote, nearMissReasons, passesScope, reasonCounts,
} from './near-miss.js';

describe('nearMissReasons', () => {
  it('keeps only known reasons, in canonical order, without repeats', () => {
    expect(nearMissReasons({ near_miss: { reasons: ['older_than_max_age', 'bogus', 'intern_or_coop', 'intern_or_coop'] } }))
      .toEqual(['intern_or_coop', 'older_than_max_age']);
  });

  it('is empty for curated jobs and junk', () => {
    expect(nearMissReasons({})).toEqual([]);
    expect(nearMissReasons({ near_miss: 'x' })).toEqual([]);
    expect(nearMissReasons(null)).toEqual([]);
  });

  it('has a label, tag and explanation for every reason', () => {
    for (const r of NEAR_MISS_REASONS) expect(Object.keys(NEAR_MISS_INFO[r])).toEqual(['label', 'tag', 'why']);
  });
});

describe('passesScope', () => {
  it('always shows curated rows and only fully-toggled near misses', () => {
    const none = new Set();
    expect(passesScope({ nearMiss: [] }, none)).toBe(true);
    expect(passesScope({ nearMiss: ['intern_or_coop'] }, none)).toBe(false);
    expect(passesScope({ nearMiss: ['intern_or_coop'] }, new Set(['intern_or_coop']))).toBe(true);
    expect(passesScope({ nearMiss: ['intern_or_coop', 'older_than_max_age'] }, new Set(['intern_or_coop']))).toBe(false);
    expect(passesScope({ nearMiss: ['intern_or_coop', 'older_than_max_age'] }, new Set(['intern_or_coop', 'older_than_max_age']))).toBe(true);
    expect(passesScope({}, none)).toBe(true);
  });
});

describe('reasonCounts / nearMissNote', () => {
  it('counts every reason, zeros included, in order', () => {
    const jobs = [{ nearMiss: ['intern_or_coop'] }, { nearMiss: ['intern_or_coop', 'level_iii_plus'] }, { nearMiss: [] }];
    expect(reasonCounts(jobs)).toEqual([['intern_or_coop', 2], ['level_iii_plus', 1], ['outside_target_countries', 0], ['older_than_max_age', 0]]);
    expect(reasonCounts([])).toEqual(NEAR_MISS_REASONS.map((r) => [r, 0]));
  });

  it('explains a near miss in one sentence and says nothing for curated rows', () => {
    expect(nearMissNote({ nearMiss: ['level_iii_plus', 'outside_target_countries'] }))
      .toBe('Not in the curated set: a level III or higher title; located outside the United States, Canada and India.');
    expect(nearMissNote({ nearMiss: [] })).toBe('');
  });
});
