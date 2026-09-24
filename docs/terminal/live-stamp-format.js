// Pure-JS helpers for the LIVE indicator. No JSX so the file is also usable
// from Node for unit testing.
//
// Exposes on window: formatLiveStamp, liveStampState
// In Node: exported via module.exports.
(function (global) {
  // The scraper is scheduled every 30 min, but GitHub Actions cron is best-
  // effort: scheduled runs can land late under load, and a run that overlaps
  // an in-flight one waits in the workflow's concurrency queue. Effective
  // cadence is 30-60 min, with occasional multi-hour gaps.
  //
  // The chip is meant to warn that the pipeline is genuinely broken, not
  // flap on normal cron jitter. 24 h gives a full day of tolerance for
  // queue starvation and platform incidents while still alerting if the
  // scraper has been completely down for a day.
  var STALE_MS = 24 * 60 * 60 * 1000;

  function liveStampState(isoString, now) {
    if (!isoString) return { kind: 'offline' };
    var t = Date.parse(isoString);
    if (!isFinite(t)) return { kind: 'offline' };
    var age = (now instanceof Date ? now.getTime() : Number(now)) - t;
    if (age > STALE_MS) return { kind: 'stale', ageMs: age, when: new Date(t) };
    return { kind: 'live', ageMs: age, when: new Date(t) };
  }

  function formatLiveStamp(isoString, now) {
    var state = liveStampState(isoString, now);
    if (state.kind === 'offline') return { label: 'OFFLINE', dot: '#888' };
    // Status only, no clock time: a formatted timestamp rendered once per
    // page load in the viewer's timezone read as stale/confusing to people
    // across regions, and the LIVE/STALE state already carries the signal.
    if (state.kind === 'stale') return { label: 'STALE', dot: '#e0a23a' };
    return { label: 'LIVE', dot: '#5fd28a' };
  }

  global.formatLiveStamp = formatLiveStamp;
  global.liveStampState = liveStampState;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { formatLiveStamp: formatLiveStamp, liveStampState: liveStampState, STALE_MS: STALE_MS };
  }
})(typeof window !== 'undefined' ? window : globalThis);
