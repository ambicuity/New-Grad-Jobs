// Migrated from tests/terminal/test_live_stamp.cjs.
import { describe, expect, it } from 'vitest';
import { STALE_MS, formatLiveStamp, liveStampState } from './live-stamp.js';

const GEN = '2026-05-16T21:32:00Z';
const at = (iso) => new Date(iso);

describe('formatLiveStamp', () => {
  it('STALE_MS is 24 hours', () => {
    expect(STALE_MS).toBe(24 * 60 * 60 * 1000);
  });

  it('returns LIVE when generated_at is fresh', () => {
    expect(formatLiveStamp(GEN, at('2026-05-16T21:33:00Z'))).toEqual({ label: 'LIVE', dot: '#5fd28a' });
  });

  it('never exposes a timestamp (the chip shows status only)', () => {
    const now = at('2026-05-16T21:33:00Z');
    for (const iso of [GEN, '2026-05-10T00:00:00Z', null]) {
      expect(Object.keys(formatLiveStamp(iso, now)).sort()).toEqual(['dot', 'label']);
    }
  });

  it.each([
    ['1 hour', '2026-05-16T22:32:00Z'],
    ['12 hours', '2026-05-17T09:32:00Z'],
  ])('is still LIVE after %s', (_label, now) => {
    expect(formatLiveStamp(GEN, at(now)).label).toBe('LIVE');
  });

  it('returns STALE after 25 hours (past the 24 h threshold)', () => {
    expect(formatLiveStamp(GEN, at('2026-05-17T22:32:00Z'))).toEqual({ label: 'STALE', dot: '#e0a23a' });
  });

  it('returns LIVE right at the boundary (1 ms before 24 h)', () => {
    const now = new Date(Date.parse(GEN) + STALE_MS - 1);
    expect(formatLiveStamp(GEN, now).label).toBe('LIVE');
  });

  it.each([null, undefined, '', 'not-a-date'])('returns OFFLINE for %j', (value) => {
    expect(formatLiveStamp(value, new Date())).toEqual({ label: 'OFFLINE', dot: '#888' });
  });

  it('accepts epoch-ms numbers for now', () => {
    expect(formatLiveStamp(GEN, Date.parse(GEN) + 1000).label).toBe('LIVE');
  });
});

describe('liveStampState', () => {
  it('exposes age and parsed time', () => {
    const state = liveStampState(GEN, at('2026-05-16T21:35:00Z'));
    expect(state.kind).toBe('live');
    expect(state.ageMs).toBe(3 * 60 * 1000);
    expect(state.when.toISOString()).toBe('2026-05-16T21:32:00.000Z');
  });

  it('flips to stale once past 24 h', () => {
    const now = new Date(Date.parse(GEN) + STALE_MS + 1000);
    expect(liveStampState(GEN, now).kind).toBe('stale');
  });

  it('is offline without a timestamp', () => {
    expect(liveStampState(undefined, new Date())).toEqual({ kind: 'offline' });
  });
});
