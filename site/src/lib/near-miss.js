// The near-miss tier. The scraper publishes jobs that fail exactly the soft
// rules (internship/co-op, level III+, outside US/CA/IN, older than the
// curated window) in jobs-extended.json with the reasons attached
// (scripts/ngj/filters.py NEAR_MISS_REASONS). The board loads that file only
// when a WIDEN SCOPE toggle is on, and a near miss is shown only when every
// one of its reasons is toggled on, so a default view is always the curated set.

/** Reason ids exactly as the scraper publishes them, in display order. */
export const NEAR_MISS_REASONS = Object.freeze([
  'intern_or_coop',
  'level_iii_plus',
  'outside_target_countries',
  'older_than_max_age',
]);

/** Chip label, short row tag and a one-line explanation per reason. */
export const NEAR_MISS_INFO = Object.freeze({
  intern_or_coop: { label: 'internships & co-ops', tag: 'intern', why: 'an internship, co-op, student placement or summer program' },
  level_iii_plus: { label: 'level III+', tag: 'L3+', why: 'a level III or higher title' },
  outside_target_countries: { label: 'outside US / CA / IN', tag: 'abroad', why: 'located outside the United States, Canada and India' },
  older_than_max_age: { label: 'posted 60–120 days ago', tag: 'older', why: 'posted more than 60 days ago' },
});

export const isNearMissReason = (value) => NEAR_MISS_REASONS.includes(value);

/**
 * Reasons on a raw published job: only known ids, in canonical order, no repeats.
 * @param {object} raw  jobs-extended.json entry (or any job; curated jobs yield []).
 * @returns {string[]}
 */
export function nearMissReasons(raw) {
  const list = raw && raw.near_miss && Array.isArray(raw.near_miss.reasons) ? raw.near_miss.reasons : [];
  const set = new Set(list.filter(isNearMissReason));
  return NEAR_MISS_REASONS.filter((r) => set.has(r));
}

/**
 * Whether a row may be shown given the WIDEN SCOPE toggles: curated rows
 * always, near misses only when every reason is toggled on.
 * @param {{nearMiss: string[]}} job
 * @param {Set<string>} include
 */
export function passesScope(job, include) {
  const reasons = job && Array.isArray(job.nearMiss) ? job.nearMiss : [];
  return reasons.every((r) => include.has(r));
}

/** [reason, count] for the near-miss rows, in NEAR_MISS_REASONS order (zero counts kept). */
export function reasonCounts(jobs) {
  const counts = new Map(NEAR_MISS_REASONS.map((r) => [r, 0]));
  for (const j of jobs || []) {
    for (const r of (j && j.nearMiss) || []) counts.set(r, (counts.get(r) || 0) + 1);
  }
  return NEAR_MISS_REASONS.map((r) => [r, counts.get(r)]);
}

/** One sentence for the detail pane: why this row is not in the curated set. */
export function nearMissNote(job) {
  const reasons = job && Array.isArray(job.nearMiss) ? job.nearMiss : [];
  if (!reasons.length) return '';
  return `Not in the curated set: ${reasons.map((r) => NEAR_MISS_INFO[r].why).join('; ')}.`;
}
