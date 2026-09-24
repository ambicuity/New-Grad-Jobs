// Time helpers for the job list. Every function takes `now` explicitly
// (defaulting to the wall clock) so it is deterministic under test.

const HOUR_MS = 3600000;

// ISO date-time with no zone designator ("2026-09-24T14:50:21.85"). The
// scraper writes UTC, so a bare timestamp is read as UTC rather than the
// viewer's local time (which would skew ages by the viewer's UTC offset).
const NAIVE_ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/;

/**
 * Parse a scraper timestamp to epoch ms. Accepts Z-suffixed / offset ISO
 * strings, bare (UTC) ISO date-times and plain dates. Returns NaN when the
 * input is missing or unparseable.
 * @param {string|null|undefined} value
 * @returns {number}
 */
export function parseTimestamp(value) {
  if (typeof value !== 'string' || !value) return NaN;
  const text = NAIVE_ISO_RE.test(value) ? `${value}Z` : value;
  return Date.parse(text);
}

/**
 * Compact age of a posting: "now", "5h", "3d", "2w", "4mo" ("—" if unknown).
 * @param {string|null|undefined} postedAt
 * @param {number} [now]
 */
export function ageString(postedAt, now = Date.now()) {
  if (!postedAt) return '—';
  const t = parseTimestamp(postedAt);
  if (Number.isNaN(t)) return '—';
  const ms = now - t;
  if (ms < 0) return 'now';
  const hours = Math.floor(ms / HOUR_MS);
  if (hours < 1) return 'now';
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d`;
  if (days < 30) return `${Math.floor(days / 7)}w`;
  return `${Math.floor(days / 30)}mo`;
}

/**
 * Relative age used for GitHub commits: "42s", "5m", "3h", "2d", "1w", "4mo", "2y".
 * @param {string|null|undefined} iso
 * @param {number} [now]
 */
export function formatAgo(iso, now = Date.now()) {
  const t = parseTimestamp(iso);
  if (!t) return '—';
  const diffSec = Math.max(0, (now - t) / 1000);
  if (diffSec < 60) return `${Math.round(diffSec)}s`;
  if (diffSec < 3600) return `${Math.round(diffSec / 60)}m`;
  if (diffSec < 86400) return `${Math.round(diffSec / 3600)}h`;
  if (diffSec < 86400 * 7) return `${Math.round(diffSec / 86400)}d`;
  if (diffSec < 86400 * 30) return `${Math.round(diffSec / (86400 * 7))}w`;
  if (diffSec < 86400 * 365) return `${Math.round(diffSec / (86400 * 30))}mo`;
  return `${Math.round(diffSec / (86400 * 365))}y`;
}
