import { describe, expect, it } from 'vitest';
import {
  MAX_SIGNAL_LENGTH, MAX_SIGNAL_WORDS, PRESETS, TIER_KEYS, cleanWords, filterCorpus, parseCorpusPayload, sortNewest, tierCounts,
} from './explore.js';

const PAYLOAD = {
  meta: { schema_version: 'corpus-1', total: 6, fields: ['company', 'title', 'location', 'source', 'posted_at', 'category', 'tier', 'url'] },
  rows: [
    ['Acme', 'Software Engineer, New Grad', 'Austin, TX', 'Greenhouse', '2026-09-20', 'software_engineering', 0, 'https://a.test/1'],
    ['Acme', 'Software Engineer Intern', 'Austin, TX', 'Greenhouse', '2026-09-22', 'software_engineering', 1, 'https://a.test/2'],
    ['Beta', 'Senior Rust Engineer', 'Remote - US', 'Ashby', '2026-09-21', 'software_engineering', 2, 'https://a.test/3'],
    ['Beta', 'Rust Engineer', 'Berlin, Germany', 'Ashby', '', 'software_engineering', 2, 'javascript:alert(1)'],
    ['Gamma', 'Trustworthy AI Lead', 'NYC', 'Lever', '2026-09-19', 'data_ml', 2, 'https://a.test/5'],
    ['Gamma', 'Software Engineer II', 'NYC', 'Lever', '2026-09-23', 'software_engineering', 2, 'https://a.test/6'],
    ['bad row'],
    ['NoTier', 'Engineer', 'X', 'Y', '', 'other', 9, 'https://a.test/9'],
  ],
};

describe('parseCorpusPayload', () => {
  it('maps rows, drops malformed ones and unsafe urls', () => {
    const { rows, meta } = parseCorpusPayload(PAYLOAD);
    expect(meta.total).toBe(6);
    expect(rows).toHaveLength(6);
    expect(rows[0]).toMatchObject({ id: 'c0', co: 'Acme', title: 'Software Engineer, New Grad', tier: 'curated', url: 'https://a.test/1' });
    expect(rows[1].tier).toBe('near_miss');
    expect(rows[3].url).toBe('');
    expect(rows[0].hay).toBe('acme software engineer, new grad austin, tx');
  });

  it('rejects payloads without rows or with a different field list', () => {
    expect(() => parseCorpusPayload({})).toThrow(/rows/);
    expect(() => parseCorpusPayload({ meta: { fields: ['x'] }, rows: [] })).toThrow(/fields/);
  });
});

describe('cleanWords', () => {
  it('trims, dedupes case-insensitively, bounds length and count', () => {
    expect(cleanWords([' Rust ', 'rust', '', 3, 'c++', 'a  b'])).toEqual(['Rust', 'c++', 'a b']);
    expect(cleanWords(['x'.repeat(100)])[0]).toHaveLength(MAX_SIGNAL_LENGTH);
    expect(cleanWords(Array.from({ length: 50 }, (_, i) => `w${i}`))).toHaveLength(MAX_SIGNAL_WORDS);
    expect(cleanWords(null)).toEqual([]);
  });
});

describe('filterCorpus', () => {
  const { rows } = parseCorpusPayload(PAYLOAD);
  const titles = (out) => out.map((r) => r.title);

  it('returns everything with an empty spec', () => {
    expect(filterCorpus(rows)).toHaveLength(6);
  });

  it('include words keep any match with scraper semantics; exclude words drop', () => {
    expect(titles(filterCorpus(rows, { include: ['rust'] }))).toEqual(['Senior Rust Engineer', 'Rust Engineer']);
    expect(titles(filterCorpus(rows, { include: ['rust'], exclude: ['senior'] }))).toEqual(['Rust Engineer']);
    expect(titles(filterCorpus(rows, { include: ['engineer ii'] }))).toEqual(['Software Engineer II']);
  });

  it('tier toggles and the free-text query narrow further', () => {
    expect(titles(filterCorpus(rows, { tiers: new Set(['curated', 'near_miss']) }))).toEqual(['Software Engineer, New Grad', 'Software Engineer Intern']);
    expect(titles(filterCorpus(rows, { q: 'gamma nyc' }))).toEqual(['Trustworthy AI Lead', 'Software Engineer II']);
    expect(filterCorpus(rows, { include: ['rust'], tiers: new Set(['curated']) })).toEqual([]);
  });
});

describe('tierCounts / sortNewest / PRESETS', () => {
  const { rows } = parseCorpusPayload(PAYLOAD);

  it('counts every tier in order and sorts newest first with undated last', () => {
    expect(tierCounts(rows)).toEqual([['curated', 1], ['near_miss', 1], ['out', 4]]);
    expect(tierCounts([])).toEqual(TIER_KEYS.map((k) => [k, 0]));
    expect(sortNewest(rows).map((r) => r.posted)).toEqual(['2026-09-23', '2026-09-22', '2026-09-21', '2026-09-20', '2026-09-19', '']);
  });

  it('every preset is a valid signal set that matches something plausible', () => {
    for (const p of PRESETS) {
      expect(p.id).toMatch(/^[a-z0-9]+$/);
      expect(cleanWords(p.include)).toEqual(p.include);
      expect(cleanWords(p.exclude)).toEqual(p.exclude);
    }
    expect(filterCorpus(rows, PRESETS.find((p) => p.id === 'languages')).map((r) => r.title)).toEqual(['Rust Engineer']);
    expect(filterCorpus(rows, PRESETS.find((p) => p.id === 'level2')).map((r) => r.title)).toEqual(['Software Engineer II']);
  });
});
