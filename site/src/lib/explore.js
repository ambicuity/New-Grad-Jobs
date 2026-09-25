// EXPLORE: every posting the scraper saw this run (corpus-index.json), before
// any new-grad rule, filtered by the viewer's own signals. Pure functions;
// the matcher is the parity-tested port of the scraper's (lib/signals.js), so
// a word here means exactly what it means in config.yml.

import { safeHttpUrl } from './safe-url.js';
import { compileSignalSet } from './signals.js';

/** Tier codes exactly as corpus-index.json publishes them. */
export const TIERS = Object.freeze([
  { code: 0, key: 'curated', label: 'curated', tag: 'board', why: 'on the board' },
  { code: 1, key: 'near_miss', label: 'near miss', tag: 'near', why: 'fails one soft rule' },
  { code: 2, key: 'out', label: 'out', tag: 'out', why: 'fails a hard rule or has no early-career signal' },
]);
export const TIER_KEYS = Object.freeze(TIERS.map((t) => t.key));
const TIER_BY_CODE = new Map(TIERS.map((t) => [t.code, t]));
const FIELDS = ['company', 'title', 'location', 'source', 'posted_at', 'category', 'tier', 'url'];

/** Word limits for a viewer signal set (shared with the URL state). */
export const MAX_SIGNAL_WORDS = 20;
export const MAX_SIGNAL_LENGTH = 40;

/**
 * Ready-made signal sets. Each is a real, explainable rule; none claims to
 * be "new grad" — the tiers already say where a row landed.
 */
export const PRESETS = Object.freeze([
  {
    id: 'level2', label: 'level II / L4 software',
    include: ['engineer ii', 'sde ii', 'developer ii', 'l4', 'e4'],
    exclude: ['senior', 'staff', 'principal', 'lead', 'manager', 'intern'],
  },
  {
    id: 'years', label: '"0–2 years" wording',
    include: ['0-2 years', '0-1 years', '1-2 years', 'entry level', 'entry-level'],
    exclude: ['senior', 'staff', 'principal'],
  },
  {
    id: 'unlevelled', label: 'unlevelled software titles',
    include: ['software engineer', 'software developer', 'developer', 'programmer'],
    exclude: ['senior', 'sr', 'staff', 'principal', 'lead', 'manager', 'director', 'architect', 'intern', 'internship'],
  },
  {
    id: 'languages', label: 'rust / go / c++ roles',
    include: ['rust', 'go', 'golang', 'c++'],
    exclude: ['senior', 'staff', 'principal', 'lead', 'manager', 'intern'],
  },
]);

/** Clean a list of viewer words: strings only, trimmed, deduped, bounded. */
export function cleanWords(words) {
  const out = [];
  const seen = new Set();
  for (const raw of Array.isArray(words) ? words : []) {
    if (typeof raw !== 'string') continue;
    const w = raw.trim().replace(/\s+/g, ' ').slice(0, MAX_SIGNAL_LENGTH);
    const key = w.toLowerCase();
    if (!w || seen.has(key)) continue;
    seen.add(key);
    out.push(w);
    if (out.length >= MAX_SIGNAL_WORDS) break;
  }
  return out;
}

/**
 * corpus-index.json → row objects. Malformed rows are dropped, never guessed.
 * @returns {{rows: object[], meta: object}}
 */
export function parseCorpusPayload(payload) {
  if (!payload || typeof payload !== 'object' || !Array.isArray(payload.rows)) {
    throw new Error('corpus payload has no "rows" array');
  }
  const meta = payload.meta && typeof payload.meta === 'object' ? payload.meta : {};
  if (Array.isArray(meta.fields) && meta.fields.join() !== FIELDS.join()) {
    throw new Error(`corpus fields ${meta.fields.join()} do not match ${FIELDS.join()}`);
  }
  const rows = [];
  payload.rows.forEach((r, i) => {
    if (!Array.isArray(r) || r.length !== FIELDS.length) return;
    const [co, title, loc, src, posted, cat, tier, url] = r;
    if (typeof title !== 'string' || !title || !TIER_BY_CODE.has(tier)) return;
    const row = {
      id: `c${i}`,
      co: typeof co === 'string' ? co : '',
      title,
      loc: typeof loc === 'string' ? loc : '',
      src: typeof src === 'string' ? src : '',
      posted: typeof posted === 'string' ? posted : '',
      cat: typeof cat === 'string' ? cat : '',
      tier: TIER_BY_CODE.get(tier).key,
      url: safeHttpUrl(url),
    };
    row.hay = `${row.co} ${row.title} ${row.loc}`.toLowerCase();
    rows.push(row);
  });
  return { rows, meta };
}

/** [tierKey, count] for every tier, zeros kept, in TIERS order. */
export function tierCounts(rows) {
  const counts = new Map(TIER_KEYS.map((k) => [k, 0]));
  for (const r of rows || []) counts.set(r.tier, (counts.get(r.tier) || 0) + 1);
  return TIER_KEYS.map((k) => [k, counts.get(k)]);
}

/**
 * Apply the viewer's signal set, tier toggles and free-text query.
 * Include words: any match keeps (none = everything). Exclude words: any
 * match drops. Tiers: a Set of tier keys; empty means all. Query: every
 * whitespace-separated term must appear in company, title or location.
 * @param {object[]} rows
 * @param {{include?: string[], exclude?: string[], tiers?: Set<string>, q?: string}} spec
 */
export function filterCorpus(rows, { include = [], exclude = [], tiers = new Set(), q = '' } = {}) {
  const set = compileSignalSet({ include: cleanWords(include), exclude: cleanWords(exclude) });
  const terms = String(q || '').toLowerCase().split(/\s+/).filter(Boolean);
  const tierOn = tiers && tiers.size ? (r) => tiers.has(r.tier) : () => true;
  return (rows || []).filter((r) => tierOn(r) && set.test(r.title) && terms.every((t) => r.hay.includes(t)));
}

/** Newest first (undated last), then company and title; never mutates. */
export function sortNewest(rows) {
  return [...(rows || [])].sort((a, b) => (b.posted || '').localeCompare(a.posted || '') || a.co.localeCompare(b.co) || a.title.localeCompare(b.title));
}
