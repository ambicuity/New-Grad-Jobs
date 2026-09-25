import { describe, expect, it } from 'vitest';
import {
  compTuple, dedupeIds, deriveRmt, deriveType, mapJob, normalizeJobsPayload, searchHaystack,
} from './jobs.js';
import { CATEGORY_TYPE, TYPE_LABEL, TYPE_ORDER } from './taxonomy.js';

const NOW = Date.parse('2026-09-24T16:00:00Z');

const RAW = {
  job_id: 'job_4e67aada0c997e69c1a7',
  id: 'palantir-fde-kitsap',
  company: 'Palantir',
  title: 'Forward Deployed Software Engineer - US Government',
  location: 'Kitsap, WA',
  url: 'https://jobs.lever.co/palantir/a2e9',
  posted_at: '2026-09-24T14:50:21Z',
  source: 'Lever',
  category: { id: 'software_engineering' },
  company_tier: { tier: 'unicorn' },
  flags: { no_sponsorship: false, us_citizenship_required: false },
  comp: { min: 120000, max: 180400, currency: 'USD' },
};

describe('deriveType', () => {
  it('maps every canonical category id to its type code', () => {
    for (const [id, code] of Object.entries(CATEGORY_TYPE)) {
      expect(deriveType({ category: { id } })).toBe(code);
    }
  });

  it('falls back to OTHER for unknown or missing categories', () => {
    expect(deriveType({ category: { id: 'astrology' } })).toBe('OTHER');
    expect(deriveType({})).toBe('OTHER');
    expect(deriveType(null)).toBe('OTHER');
  });

  it('keeps TYPE_LABEL, TYPE_ORDER and CATEGORY_TYPE codes in step', () => {
    const codes = new Set(Object.values(CATEGORY_TYPE));
    expect(new Set(Object.keys(TYPE_LABEL))).toEqual(codes);
    expect(new Set(TYPE_ORDER)).toEqual(codes);
  });
});

describe('deriveRmt', () => {
  it.each([
    [{ location: 'Remote - US' }, 'remote'],
    [{ location: 'New York, NY (Hybrid)' }, 'hybrid'],
    [{ location: 'San Francisco, hybrid remote' }, 'hybrid'],
    [{ location: 'Austin, TX', title: 'SWE (Remote)' }, 'remote'],
    [{ location: 'Austin, TX' }, 'onsite'],
    [{ location: 'Remotely, TX' }, 'onsite'],
    [{}, 'onsite'],
  ])('%j → %s', (j, expected) => {
    expect(deriveRmt(j)).toBe(expected);
  });
});

describe('compTuple', () => {
  it('rounds dollars to $k', () => {
    expect(compTuple(RAW)).toEqual([120, 180]);
  });

  it.each([{ comp: null }, { comp: { min: 1 } }, { comp: { max: 1 } }, {}])('is [null, null] for %j', (j) => {
    expect(compTuple(j)).toEqual([null, null]);
  });
});

describe('mapJob', () => {
  it('maps a complete record, keyed by the stable job_id', () => {
    expect(mapJob(RAW, NOW)).toEqual({
      id: 'job_4e67aada0c997e69c1a7',
      co: 'Palantir',
      role: 'Forward Deployed Software Engineer - US Government',
      loc: 'Kitsap, WA',
      metro: 'Kitsap, WA',
      country: 'US',
      url: 'https://jobs.lever.co/palantir/a2e9',
      rmt: 'onsite',
      visa: true,
      visaNote: null,
      tier: 'unicorn',
      comp: [120, 180],
      type: 'SWE',
      posted: '1h',
      postedTs: Date.UTC(2026, 8, 24, 14, 50, 21),
      firstSeenTs: null,
      jobId: 'job_4e67aada0c997e69c1a7',
      desc: '',
      closed: false,
      nearMiss: [],
      hay: 'palantir forward deployed software engineer - us government kitsap, wa',
    });
  });

  it('never invents data: no deadline, stack, cohort, level or placeholder description', () => {
    const j = mapJob(RAW, NOW);
    for (const k of ['dl', 'stack', 'cohort', 'level', 'size']) expect(j).not.toHaveProperty(k);
    expect(j.desc).toBe('');
  });

  it('survives a record with every field missing', () => {
    const j = mapJob({}, NOW);
    expect(j).toMatchObject({
      id: '', co: '—', role: '—', loc: '—', url: '', rmt: 'onsite', visa: true, visaNote: null, tier: 'other',
      comp: [null, null], type: 'OTHER', posted: '—', postedTs: 0, jobId: '', desc: '', closed: false,
    });
    expect(mapJob(undefined, NOW).co).toBe('—');
  });

  it('falls back to the slug id when there is no job_id', () => {
    expect(mapJob({ ...RAW, job_id: undefined }, NOW).id).toBe('palantir-fde-kitsap');
  });

  it('records which restriction the posting states (visa=false means "restriction stated")', () => {
    expect(mapJob({ ...RAW, flags: { no_sponsorship: true } }, NOW)).toMatchObject({ visa: false, visaNote: 'no-sponsorship' });
    expect(mapJob({ ...RAW, flags: { us_citizenship_required: true } }, NOW)).toMatchObject({ visa: false, visaNote: 'citizenship' });
    expect(mapJob({ ...RAW, flags: { no_sponsorship: true, us_citizenship_required: true } }, NOW).visaNote).toBe('citizenship');
  });

  it('keeps the company tier as published (unknown tiers → other)', () => {
    expect(mapJob({ ...RAW, company_tier: { tier: 'faang_plus' } }, NOW).tier).toBe('faang_plus');
    expect(mapJob({ ...RAW, company_tier: { tier: 'mystery' } }, NOW).tier).toBe('other');
  });

  it('flags closed postings', () => {
    expect(mapJob({ ...RAW, is_closed: true }, NOW).closed).toBe(true);
    expect(mapJob({ ...RAW, is_closed: 'yes' }, NOW).closed).toBe(false);
  });

  it('only keeps http(s) application URLs', () => {
    expect(mapJob({ ...RAW, url: 'javascript:alert(1)' }, NOW).url).toBe('');
    expect(mapJob({ ...RAW, url: 'http://example.com/job' }, NOW).url).toBe('http://example.com/job');
  });

  it('keeps a real description (jobs.json fallback) but not a stub', () => {
    const long = 'x'.repeat(61);
    expect(mapJob({ ...RAW, description: long }, NOW).desc).toBe(long);
    expect(mapJob({ ...RAW, description: 'short' }, NOW).desc).toBe('');
  });

  it('ignores a non-string job_id and stringifies numeric ids', () => {
    const j = mapJob({ ...RAW, job_id: 12, id: 7 }, NOW);
    expect(j.jobId).toBe('');
    expect(j.id).toBe('7');
  });

  it('treats a zone-less posted_at as UTC', () => {
    const j = mapJob({ ...RAW, posted_at: '2026-09-24T14:50:21.850000' }, NOW);
    expect(j.postedTs).toBe(Date.UTC(2026, 8, 24, 14, 50, 21, 850));
    expect(j.posted).toBe('1h');
  });
});

describe('searchHaystack', () => {
  it('is the lower-cased company, role and location', () => {
    expect(searchHaystack({ co: 'ACME', role: 'SWE II', loc: 'NYC' })).toBe('acme swe ii nyc');
  });
});

describe('dedupeIds', () => {
  it('suffixes repeated ids with #n and leaves the input untouched', () => {
    const input = [{ id: 'a' }, { id: 'b' }, { id: 'a' }, { id: 'a' }];
    const out = dedupeIds(input);
    expect(out.map((j) => j.id)).toEqual(['a', 'b', 'a#2', 'a#3']);
    expect(input.map((j) => j.id)).toEqual(['a', 'b', 'a', 'a']);
  });
});

describe('normalizeJobsPayload', () => {
  it('maps jobs and returns meta', () => {
    const out = normalizeJobsPayload({ meta: { generated_at: 'x' }, jobs: [RAW, RAW] }, NOW);
    expect(out.meta).toEqual({ generated_at: 'x' });
    expect(out.jobs.map((j) => j.id)).toEqual(['job_4e67aada0c997e69c1a7', 'job_4e67aada0c997e69c1a7#2']);
  });

  it('defaults meta to {}', () => {
    expect(normalizeJobsPayload({ jobs: [] }, NOW)).toEqual({ jobs: [], meta: {} });
  });

  it.each([null, {}, { jobs: 'nope' }, 'text'])('throws on a payload without a jobs array: %j', (p) => {
    expect(() => normalizeJobsPayload(p, NOW)).toThrow(/no "jobs" array/);
  });
});

describe('mapJob firstSeenTs', () => {
  it('reads first_seen as epoch ms, null when absent or invalid', () => {
    expect(mapJob({ first_seen: '2026-09-25T12:00:00Z' }).firstSeenTs).toBe(Date.parse('2026-09-25T12:00:00Z'));
    expect(mapJob({}).firstSeenTs).toBeNull();
    expect(mapJob({ first_seen: 'nope' }).firstSeenTs).toBeNull();
  });
});
