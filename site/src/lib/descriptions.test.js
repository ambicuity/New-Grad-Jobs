import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  DESCRIPTION_SHARD_KEYS, descriptionShard, descriptionShardUrl, lookupDescription,
} from './descriptions.js';

const siteRoot = fileURLToPath(new URL('../../', import.meta.url));
const readJson = (rel) => JSON.parse(readFileSync(`${siteRoot}${rel}`, 'utf8'));

// Mirrors tests/test_publish.py for scripts/publish.py description_shard().
describe('descriptionShard (parity with scripts/publish.py)', () => {
  it('uses the first hex digit of the job_id', () => {
    expect(descriptionShard('job_a1b2c3')).toBe('a');
    expect(descriptionShard('job_0fffff')).toBe('0');
  });

  it('lower-cases the digit like publish.py', () => {
    expect(descriptionShard('job_F00')).toBe('f');
  });

  it.each(['', 'job_', 'slug-abc', 'job_zz', null, undefined, 42])('rejects malformed id %j', (bad) => {
    expect(descriptionShard(bad)).toBeNull();
  });

  it('covers all sixteen hex digits', () => {
    expect(DESCRIPTION_SHARD_KEYS).toEqual('0123456789abcdef'.split(''));
  });

  it('builds relative shard URLs', () => {
    expect(descriptionShardUrl('a')).toBe('./descriptions/a.json');
  });
});

describe('lookupDescription', () => {
  it('returns the text for a job in the shard', () => {
    expect(lookupDescription({ job_a1: 'Alpha role' }, 'job_a1')).toBe('Alpha role');
  });

  it('returns null for missing ids, non-string values and empty shards', () => {
    expect(lookupDescription({ job_a1: 'x' }, 'job_a2')).toBeNull();
    expect(lookupDescription({ job_a1: 42 }, 'job_a1')).toBeNull();
    expect(lookupDescription(null, 'job_a1')).toBeNull();
    expect(lookupDescription({}, 'job_a1')).toBeNull();
  });
});

describe('fixture shard contract', () => {
  it('every fixture job with a description lives in the shard descriptionShard() picks', () => {
    const { jobs } = readJson('test/fixtures/jobs.json');
    const withText = jobs.filter((j) => j.job_id && j.description);
    expect(withText.length).toBeGreaterThan(10);
    for (const j of withText) {
      const key = descriptionShard(j.job_id);
      const shard = readJson(`test/fixtures/descriptions/${key}.json`);
      expect(lookupDescription(shard, j.job_id)).toBe(j.description);
    }
  });

  // Cross-checks real publish.py output when `npm run fetch-data` has run.
  it.skipIf(!existsSync(`${siteRoot}public/descriptions/0.json`))('matches the live published shards', () => {
    const { jobs } = readJson('public/jobs.json');
    const shards = Object.fromEntries(DESCRIPTION_SHARD_KEYS.map((k) => [k, readJson(`public/descriptions/${k}.json`)]));
    const sample = jobs.filter((j) => j.job_id && j.description).slice(0, 200);
    for (const j of sample) {
      expect(lookupDescription(shards[descriptionShard(j.job_id)], j.job_id)).not.toBeNull();
    }
  });
});
