import { describe, expect, it } from 'vitest';
import { similarJobs } from './similar.js';

const job = (id, over) => ({
  id, co: 'Other', role: `Role ${id}`, loc: 'Elsewhere', type: 'SWE', postedTs: 1, closed: false, ...over,
});

describe('similarJobs', () => {
  const target = job('t', { co: 'Acme', loc: 'Austin, TX' });
  const JOBS = [
    target,
    job('ml', { type: 'ML', co: 'Acme', loc: 'Austin, TX' }), // wrong type
    job('plain-old', { postedTs: 1 }),
    job('plain-new', { postedTs: 5 }),
    job('same-loc', { loc: 'Austin, TX' }),
    job('same-co', { co: 'Acme' }),
    job('same-both', { co: 'Acme', loc: 'Austin, TX' }),
    job('closed', { co: 'Acme', loc: 'Austin, TX', closed: true }),
    job('dupe', { co: 'Acme', loc: 'Austin, TX', role: 'Role t' }), // same posting, other source
  ];

  it('ranks same-type roles: company+location, company, location, then newest', () => {
    expect(similarJobs(target, JOBS, 5).map((j) => j.id))
      .toEqual(['same-both', 'same-co', 'same-loc', 'plain-new', 'plain-old']);
  });

  it('defaults to three results and excludes the job, closed jobs and duplicates of it', () => {
    const ids = similarJobs(target, JOBS).map((j) => j.id);
    expect(ids).toHaveLength(3);
    expect(ids).not.toContain('t');
    expect(ids).not.toContain('closed');
    expect(ids).not.toContain('dupe');
  });

  it('breaks full ties by id for a stable order', () => {
    const list = [target, job('b'), job('a')];
    expect(similarJobs(target, list).map((j) => j.id)).toEqual(['a', 'b']);
  });

  it('returns [] without a job and never mutates the input', () => {
    expect(similarJobs(null, JOBS)).toEqual([]);
    const before = JOBS.map((j) => j.id);
    similarJobs(target, JOBS);
    expect(JOBS.map((j) => j.id)).toEqual(before);
  });
});
