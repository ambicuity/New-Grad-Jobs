// Pure-JS helpers for the LIVE indicator. No JSX so the file is also usable
// from Node for unit testing.
//
// Exposes on window: formatLiveStamp, liveStampState
// In Node: exported via module.exports.
(function (global) {
  // The scraper is scheduled every 5 min, but GitHub Actions cron is best-
  // effort: scheduled runs land 10-30+ min late on free-tier load, runs that
  // overlap an in-flight one are cancelled by the workflow's concurrency
  // group, and `*/5` schedules are deprioritized vs. larger intervals.
  // Effective cadence is 15-60 min, with occasional multi-hour gaps.
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
    if (state.kind === 'offline') return { label: 'OFFLINE', dot: '#888', text: '—' };
    var label = state.kind === 'stale' ? 'STALE' : 'LIVE';
    var dot = state.kind === 'stale' ? '#e0a23a' : '#5fd28a';
    // Browser locale + viewer timezone. The short tz token replaces the old
    // hardcoded "PT" suffix; viewers in PDT see "PDT", viewers in IST see "GMT+5:30",
    // etc. — whatever Intl reports for their environment.
    var text;
    try {
      var fmt = new Intl.DateTimeFormat(undefined, {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: false,
        timeZoneName: 'short',
      });
      text = fmt.format(state.when);
    } catch (e) {
      text = state.when.toISOString();
    }
    return { label: label, dot: dot, text: text };
  }

  global.formatLiveStamp = formatLiveStamp;
  global.liveStampState = liveStampState;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { formatLiveStamp: formatLiveStamp, liveStampState: liveStampState, STALE_MS: STALE_MS };
  }
})(typeof window !== 'undefined' ? window : globalThis);
