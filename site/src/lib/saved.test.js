import { describe, expect, it, vi } from 'vitest';
import {
  APPLIED_STORAGE_KEY, MAX_SAVED, SAVED_STORAGE_KEY, loadSavedIds, parseSavedIds, serializeSavedIds, storeSavedIds,
} from './saved.js';

describe('parseSavedIds', () => {
  it('reads a JSON array of job ids into a Set', () => {
    expect([...parseSavedIds('["job_a","job_b","job_a"]')]).toEqual(['job_a', 'job_b']);
  });

  it.each([null, '', 'not json', '{"a":1}', '42', 'null'])('returns an empty Set for %j', (raw) => {
    expect(parseSavedIds(raw).size).toBe(0);
  });

  it('drops non-string, empty and oversized entries', () => {
    const raw = JSON.stringify(['job_ok', 1, null, '', 'x'.repeat(201), { id: 'job_c' }]);
    expect([...parseSavedIds(raw)]).toEqual(['job_ok']);
  });

  it(`caps the list at ${MAX_SAVED} ids`, () => {
    const raw = JSON.stringify(Array.from({ length: MAX_SAVED + 5 }, (_, i) => `job_${i}`));
    expect(parseSavedIds(raw).size).toBe(MAX_SAVED);
  });

  it('round-trips through serializeSavedIds', () => {
    const s = new Set(['job_a', 'job_b']);
    expect(parseSavedIds(serializeSavedIds(s))).toEqual(s);
  });
});

describe('storage wrappers', () => {
  const memory = () => {
    const data = new Map();
    return {
      getItem: vi.fn((k) => (data.has(k) ? data.get(k) : null)),
      setItem: vi.fn((k, v) => data.set(k, v)),
    };
  };

  it('stores and loads under the versioned key', () => {
    const storage = memory();
    expect(storeSavedIds(() => storage, new Set(['job_a']))).toBe(true);
    expect(storage.setItem).toHaveBeenCalledWith(SAVED_STORAGE_KEY, '["job_a"]');
    expect([...loadSavedIds(() => storage)]).toEqual(['job_a']);
  });

  it('keeps applied jobs under their own key', () => {
    const storage = memory();
    expect(storeSavedIds(() => storage, new Set(['job_a']), APPLIED_STORAGE_KEY)).toBe(true);
    expect(storage.setItem).toHaveBeenCalledWith(APPLIED_STORAGE_KEY, '["job_a"]');
    expect([...loadSavedIds(() => storage, APPLIED_STORAGE_KEY)]).toEqual(['job_a']);
    expect(loadSavedIds(() => storage).size).toBe(0);
    expect(APPLIED_STORAGE_KEY).not.toBe(SAVED_STORAGE_KEY);
  });

  it('never throws when storage is unavailable or broken', () => {
    const throwing = () => { throw new Error('SecurityError'); };
    expect(loadSavedIds(throwing).size).toBe(0);
    expect(storeSavedIds(throwing, new Set(['a']))).toBe(false);
    const quota = { getItem: () => { throw new Error('denied'); }, setItem: () => { throw new Error('QuotaExceeded'); } };
    expect(loadSavedIds(() => quota).size).toBe(0);
    expect(storeSavedIds(() => quota, new Set(['a']))).toBe(false);
    expect(loadSavedIds(() => null).size).toBe(0);
    expect(storeSavedIds(() => undefined, new Set())).toBe(false);
  });
});
