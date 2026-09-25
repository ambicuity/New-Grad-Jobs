import { describe, expect, it, vi } from 'vitest';
import { copyText, jobShareUrl } from './share.js';

describe('jobShareUrl', () => {
  const loc = { origin: 'https://jobs.example.test', pathname: '/' };

  it('links to the static job page when the job has a stable id', () => {
    expect(jobShareUrl({ id: 'acme-swe', jobId: 'job_abc123' }, loc)).toBe('https://jobs.example.test/job/job_abc123/');
  });

  it('falls back to the board deep link without a stable id', () => {
    expect(jobShareUrl({ id: 'acme swe #2', jobId: '' }, loc)).toBe('https://jobs.example.test/?job=acme%20swe%20%232');
  });

  it('keeps a sub-path deployment', () => {
    const sub = { origin: 'https://user.github.io', pathname: '/New-Grad-Jobs/index.html' };
    expect(jobShareUrl({ id: 'x', jobId: 'job_1' }, sub)).toBe('https://user.github.io/New-Grad-Jobs/job/job_1/');
    expect(jobShareUrl({ id: 'x', jobId: '' }, { origin: 'https://user.github.io', pathname: '/New-Grad-Jobs/' }))
      .toBe('https://user.github.io/New-Grad-Jobs/?job=x');
  });

  it('never trusts an unsafe id in the path', () => {
    expect(jobShareUrl({ id: 'x', jobId: '../evil' }, loc)).toBe('https://jobs.example.test/?job=x');
    expect(jobShareUrl(null, {})).toBe('/?job=');
  });
});

describe('copyText', () => {
  it('uses the async clipboard when available', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    expect(await copyText('hello', { clipboard: { writeText } })).toBe(true);
    expect(writeText).toHaveBeenCalledWith('hello');
  });

  it('reports failure instead of throwing', async () => {
    expect(await copyText('x', { clipboard: { writeText: () => Promise.reject(new Error('denied')) } })).toBe(false);
    expect(await copyText('x', {})).toBe(false);
    expect(await copyText('x', undefined)).toBe(false);
  });
});
