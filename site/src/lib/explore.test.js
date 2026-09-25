import { describe, expect, it } from 'vitest';
import {
  EMPTY_EXPLORE, EXCLUDE_CHIPS, INCLUDE_CHIPS, MAX_SIGNAL_LENGTH, MAX_SIGNAL_WORDS, POSTED_DAYS, PRESETS, TIER_KEYS,
  categoryLabel, chipIsOn, cleanWords, facetCounts, filterCorpus, matchedWords, parseCorpusPayload, sortNewest, tierCounts, tierInfo,
  toCsv, toggleChipWords,
} from './explore.js';

const PAYLOAD = {
  meta: { schema_version: 'corpus-1', total: 6, fields: ['company', 'title', 'location', 'source', 'posted_at', 'category', 'tier', 'url'] },
  rows: [
    ['Acme', 'Software Engineer, New Grad', 'Austin, TX', 'Greenhouse', '2026-09-20', 'software_engineering', 0, 'https://a.test/1'],
    ['Acme', 'Software Engineer Intern', 'Austin, TX', 'Greenhouse', '2026-09-22', 'software_engineering', 1, 'https://a.test/2'],
    ['Beta', 'Senior Rust Engineer', 'Remote - US', 'Ashby', '2026-09-21', 'software_engineering', 2, 'https://a.test/3'],
    ['Beta', 'Rust Engineer', 'Berlin, Germany', 'Ashby', '', 'software_engineering', 2, 'javascript:alert(1)'],
    ['Gamma', 'Trustworthy AI Lead', 'Toronto, ON', 'Lever', '2026-09-19', 'data_ml', 2, 'https://a.test/5'],
    ['Gamma', 'Software Engineer II', 'NYC', 'Lever', '2026-09-23', '', 2, 'https://a.test/6'],
    ['bad row'],
    ['NoTier', 'Engineer', 'X', 'Y', '', 'other', 9, 'https://a.test/9'],
  ],
};
const NOW = new Date('2026-09-24T12:00:00Z');
const spec = (over) => ({ ...EMPTY_EXPLORE(), ...over });

describe('parseCorpusPayload', () => {
  it('maps rows, derives country, drops malformed rows and unsafe urls', () => {
    const { rows, meta } = parseCorpusPayload(PAYLOAD);
    expect(meta.total).toBe(6);
    expect(rows).toHaveLength(6);
    expect(rows[0]).toMatchObject({ id: 'c0', co: 'Acme', tier: 'curated', url: 'https://a.test/1', country: 'US', cat: 'software_engineering' });
    expect(rows[1].tier).toBe('near_miss');
    expect(rows[3].url).toBe('');
    expect(rows[3].country).toBe('');
    expect(rows[4].country).toBe('CA');
    expect(rows[5].cat).toBe('other');
    expect(rows[0].hay).toBe('acme software engineer, new grad austin, tx');
  });

  it('rejects payloads without rows or with a different field list', () => {
    expect(() => parseCorpusPayload({})).toThrow(/rows/);
    expect(() => parseCorpusPayload({ meta: { fields: ['x'] }, rows: [] })).toThrow(/fields/);
  });
});

describe('cleanWords / chips', () => {
  it('trims, dedupes case-insensitively, bounds length and count', () => {
    expect(cleanWords([' Rust ', 'rust', '', 3, 'c++', 'a  b'])).toEqual(['Rust', 'c++', 'a b']);
    expect(cleanWords(['x'.repeat(100)])[0]).toHaveLength(MAX_SIGNAL_LENGTH);
    expect(cleanWords(Array.from({ length: 50 }, (_, i) => `w${i}`))).toHaveLength(MAX_SIGNAL_WORDS);
    expect(cleanWords(null)).toEqual([]);
  });

  it('toggles a chip\'s words in and out and reports its state', () => {
    const junior = INCLUDE_CHIPS.find((c) => c.id === 'junior');
    const newgrad = INCLUDE_CHIPS.find((c) => c.id === 'newgrad');
    let words = toggleChipWords([], junior);
    expect(words).toEqual(['junior']);
    expect(chipIsOn(words, junior)).toBe(true);
    words = toggleChipWords(words, newgrad);
    expect(words).toEqual(['junior', ...newgrad.words]);
    expect(chipIsOn(['New Grad', 'new graduate', 'university grad', 'college grad'], newgrad)).toBe(true);
    words = toggleChipWords(words, newgrad);
    expect(words).toEqual(['junior']);
    expect(chipIsOn(['new grad'], newgrad)).toBe(false); // partial → off, toggling adds the rest
    expect(toggleChipWords(['new grad'], newgrad)).toEqual(newgrad.words);
  });

  it('every chip and preset is a clean word set', () => {
    for (const c of [...INCLUDE_CHIPS, ...EXCLUDE_CHIPS]) expect(cleanWords(c.words)).toEqual(c.words);
    for (const p of PRESETS) {
      expect(p.id).toMatch(/^[a-z0-9]+$/);
      expect(cleanWords(p.include)).toEqual(p.include);
      expect(cleanWords(p.exclude)).toEqual(p.exclude);
    }
  });

  it('labels categories with the board\'s short names', () => {
    expect(categoryLabel('software_engineering')).toBe('swe');
    expect(categoryLabel('healthcare')).toBe('healthcare');
    expect(categoryLabel('')).toBe('other');
  });
});

describe('filterCorpus', () => {
  const { rows } = parseCorpusPayload(PAYLOAD);
  const titles = (out) => out.map((r) => r.title);

  it('returns everything with an empty spec', () => {
    expect(filterCorpus(rows)).toHaveLength(6);
    expect(filterCorpus(rows, undefined)).toHaveLength(6);
  });

  it('include words keep any match with scraper semantics; exclude words drop', () => {
    expect(titles(filterCorpus(rows, spec({ include: ['rust'] })))).toEqual(['Senior Rust Engineer', 'Rust Engineer']);
    expect(titles(filterCorpus(rows, spec({ include: ['rust'], exclude: ['senior'] })))).toEqual(['Rust Engineer']);
    expect(titles(filterCorpus(rows, spec({ include: ['engineer ii'] })))).toEqual(['Software Engineer II']);
  });

  it('facets narrow: tier, role, source, country, posted window, query', () => {
    expect(titles(filterCorpus(rows, spec({ tiers: new Set(['curated', 'near_miss']) })))).toEqual(['Software Engineer, New Grad', 'Software Engineer Intern']);
    expect(titles(filterCorpus(rows, spec({ roles: new Set(['data_ml']) })))).toEqual(['Trustworthy AI Lead']);
    expect(titles(filterCorpus(rows, spec({ sources: new Set(['Ashby']) })))).toHaveLength(2);
    expect(titles(filterCorpus(rows, spec({ countries: new Set(['CA']) })))).toEqual(['Trustworthy AI Lead']);
    expect(titles(filterCorpus(rows, spec({ posted: 1 }), { now: NOW }))).toEqual(['Software Engineer II']);
    expect(titles(filterCorpus(rows, spec({ posted: 7 }), { now: NOW }))).toHaveLength(5); // undated Berlin row excluded
    expect(titles(filterCorpus(rows, spec({ q: 'gamma' })))).toHaveLength(2);
    expect(filterCorpus(rows, spec({ include: ['rust'], tiers: new Set(['curated']) }))).toEqual([]);
  });

  it('facetCounts leave the facet itself out so its chips stay switchable', () => {
    const s = spec({ sources: new Set(['Ashby']), include: ['engineer'] });
    expect(facetCounts(rows, s, 'sources', (r) => r.src)).toEqual([['Ashby', 2], ['Greenhouse', 2], ['Lever', 1]]);
    expect(facetCounts(rows, s, 'roles', (r) => r.cat)).toEqual([['software_engineering', 2]]);
    expect(filterCorpus(rows, s, { ignore: new Set(['words']) })).toHaveLength(2);
  });
});

describe('explainability and export', () => {
  const { rows } = parseCorpusPayload(PAYLOAD);

  it('matchedWords reports which include words hit the title, with inflections', () => {
    expect(matchedWords('Senior Rust Engineer', ['rust', 'engineer', 'go'])).toEqual(['rust', 'engineer']);
    expect(matchedWords('Data Engineering Associate', ['engineer'])).toEqual(['engineer']);
    expect(matchedWords('Trustworthy AI Lead', ['rust'])).toEqual([]);
  });

  it('tierInfo explains each tier and falls back to out', () => {
    expect(tierInfo('curated').tag).toBe('board');
    expect(tierInfo('nope').key).toBe('out');
  });

  it('tierCounts and sortNewest', () => {
    expect(tierCounts(rows)).toEqual([['curated', 1], ['near_miss', 1], ['out', 4]]);
    expect(tierCounts([])).toEqual(TIER_KEYS.map((k) => [k, 0]));
    expect(sortNewest(rows).map((r) => r.posted)).toEqual(['2026-09-23', '2026-09-22', '2026-09-21', '2026-09-20', '2026-09-19', '']);
  });

  it('toCsv quotes every cell and neutralises formula injection', () => {
    const csv = toCsv([{ ...rows[0], title: '=SUM(A1) "x"', loc: 'Austin, TX' }]);
    const lines = csv.split('\r\n');
    expect(lines[0]).toBe('company,title,location,source,posted,category,tier,url');
    expect(lines[1]).toBe('"Acme","\'=SUM(A1) ""x""","Austin, TX","Greenhouse","2026-09-20","software_engineering","curated","https://a.test/1"');
    expect(toCsv([])).toBe('company,title,location,source,posted,category,tier,url\r\n');
  });

  it('posted windows are the documented days', () => {
    expect(POSTED_DAYS).toEqual([1, 7, 30]);
  });
});
