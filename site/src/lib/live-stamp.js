// Pure helpers for the LIVE / STALE / OFFLINE chip in the top bar.

// The scraper is scheduled every 30 min, but GitHub Actions cron is best-
// effort: scheduled runs can land late under load, and a run that overlaps an
// in-flight one waits in the workflow's concurrency queue. Effective cadence
// is 30-60 min, with occasional multi-hour gaps.
//
// The chip is meant to warn that the pipeline is genuinely broken, not flap
// on normal cron jitter. 24 h gives a full day of tolerance for queue
// starvation and platform incidents while still alerting if the scraper has
// been completely down for a day.
export const STALE_MS = 24 * 60 * 60 * 1000;

/**
 * @param {string|null|undefined} isoString  meta.generated_at
 * @param {Date|number} now
 * @returns {{kind: 'offline'} | {kind: 'live'|'stale', ageMs: number, when: Date}}
 */
export function liveStampState(isoString, now) {
  if (!isoString) return { kind: 'offline' };
  const t = Date.parse(isoString);
  if (!Number.isFinite(t)) return { kind: 'offline' };
  const age = (now instanceof Date ? now.getTime() : Number(now)) - t;
  if (age > STALE_MS) return { kind: 'stale', ageMs: age, when: new Date(t) };
  return { kind: 'live', ageMs: age, when: new Date(t) };
}

/**
 * Status only, no clock time: a formatted timestamp rendered once per page
 * load in the viewer's timezone read as stale/confusing to people across
 * regions, and the LIVE/STALE state already carries the signal.
 * @returns {{label: string, dot: string}}
 */
export function formatLiveStamp(isoString, now) {
  const state = liveStampState(isoString, now);
  if (state.kind === 'offline') return { label: 'OFFLINE', dot: '#888' };
  if (state.kind === 'stale') return { label: 'STALE', dot: '#e0a23a' };
  return { label: 'LIVE', dot: '#5fd28a' };
}
