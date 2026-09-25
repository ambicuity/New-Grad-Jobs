// EXPLORE: every posting the scraper saw this run (corpus-index.json), before
// any new-grad rule, filtered by the viewer's own signals and facets. Pure
// functions; the word matcher is the parity-tested port of the scraper's
// (lib/signals.js), so a word here means exactly what it means in config.yml.

import { safeHttpUrl } from './safe-url.js';
import { countryOf } from './location.js';
import { CATEGORY_TYPE, TYPE_LABEL } from './taxonomy.js';
import { compileSignalSet, compileSignals, matchesAny, TRACK_SUFFIX } from './signals.js';

/** Tier codes exactly as corpus-index.json publishes them. */
export const TIERS = Object.freeze([
  { code: 0, key: 'curated', label: 'curated', tag: 'board', why: 'on the board: passes every rule' },
  { code: 1, key: 'near_miss', label: 'near miss', tag: 'near', why: 'near miss: fails one soft rule (internship, level III+, outside US/CA/IN, or 60–120 days old)' },
  { code: 2, key: 'out', label: 'out', tag: 'out', why: 'out: a senior/manager word, no early-career signal, or no role word' },
]);
export const TIER_KEYS = Object.freeze(TIERS.map((t) => t.key));
const TIER_BY_CODE = new Map(TIERS.map((t) => [t.code, t]));
const TIER_BY_KEY = new Map(TIERS.map((t) => [t.key, t]));
const FIELDS = ['company', 'title', 'location', 'source', 'posted_at', 'category', 'tier', 'url'];

/** Word limits for a viewer signal set (shared with the URL state). */
export const MAX_SIGNAL_WORDS = 20;
export const MAX_SIGNAL_LENGTH = 40;

/** Posting-age windows for the POSTED facet, in days. */
export const POSTED_WINDOWS = Object.freeze([
  { days: 1, label: '24h' },
  { days: 7, label: '7d' },
  { days: 30, label: '30d' },
]);
export const POSTED_DAYS = Object.freeze(POSTED_WINDOWS.map((w) => w.days));

/**
 * One-click signal chips. Each toggles a small word list into the include or
 * exclude set, so the free-text editors and the chips describe one state.
 */
export const INCLUDE_CHIPS = Object.freeze([
  { id: 'newgrad', label: 'new grad', words: ['new grad', 'new graduate', 'university grad', 'college grad'] },
  { id: 'entry', label: 'entry level', words: ['entry level', 'entry-level'] },
  { id: 'junior', label: 'junior', words: ['junior'] },
  { id: 'associate', label: 'associate', words: ['associate'] },
  { id: 'early', label: 'early career', words: ['early career', 'early-career'] },
  { id: 'level12', label: 'level I / II', words: ['i', 'ii', 'level 1', 'level 2'] },
  { id: 'l34', label: 'L3 / L4', words: ['l3', 'l4', 'e3', 'e4'] },
  { id: 'years', label: '2026 / 2027', words: ['2026', '2027'] },
  { id: 'program', label: 'grad program', words: ['graduate program', 'rotational program', 'development program'] },
  { id: 'exp', label: '0–2 years', words: ['0-2 years', '0-1 years', '1-2 years'] },
]);
export const EXCLUDE_CHIPS = Object.freeze([
  { id: 'senior', label: 'senior', words: ['senior', 'sr', 'sr.'] },
  { id: 'staff', label: 'staff', words: ['staff'] },
  { id: 'principal', label: 'principal', words: ['principal', 'distinguished'] },
  { id: 'lead', label: 'lead', words: ['lead'] },
  { id: 'manager', label: 'manager', words: ['manager'] },
  { id: 'director', label: 'director / VP', words: ['director', 'vp', 'head of'] },
  { id: 'architect', label: 'architect', words: ['architect'] },
  { id: 'intern', label: 'intern', words: ['intern', 'internship'] },
  { id: 'coop', label: 'co-op', words: ['co-op', 'coop', 'co op'] },
  { id: 'years5', label: '5+ years', words: ['5+ years', '6+ years', '7+ years', '8+ years', '10+ years'] },
]);

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

const lower = (w) => w.toLowerCase();

/** True when every word of `chip` is in `words` (case-insensitive). */
export function chipIsOn(words, chip) {
  const have = new Set((words || []).map(lower));
  return chip.words.every((w) => have.has(w));
}

/** Toggle a chip's words in a word list: remove them all when on, add the missing ones when off. */
export function toggleChipWords(words, chip) {
  const list = words || [];
  if (chipIsOn(list, chip)) {
    const drop = new Set(chip.words);
    return list.filter((w) => !drop.has(lower(w)));
  }
  return cleanWords([...list, ...chip.words]);
}

/** Category id → short label for chips ("swe", "healthcare", …). */
export const categoryLabel = (id) => TYPE_LABEL[CATEGORY_TYPE[id]] || id || 'other';

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
    const location = typeof loc === 'string' ? loc : '';
    const row = {
      id: `c${i}`,
      co: typeof co === 'string' ? co : '',
      title,
      loc: location,
      src: typeof src === 'string' ? src : '',
      posted: typeof posted === 'string' ? posted : '',
      cat: typeof cat === 'string' && cat ? cat : 'other',
      tier: TIER_BY_CODE.get(tier).key,
      url: safeHttpUrl(url),
      country: countryOf(location),
    };
    row.hay = `${row.co} ${row.title} ${row.loc}`.toLowerCase();
    rows.push(row);
  });
  return { rows, meta };
}

/** @returns {{include: string[], exclude: string[], tiers: Set<string>, roles: Set<string>, sources: Set<string>, countries: Set<string>, posted: number|null, q: string}} */
export function EMPTY_EXPLORE() {
  return { include: [], exclude: [], tiers: new Set(), roles: new Set(), sources: new Set(), countries: new Set(), posted: null, q: '' };
}

const DAY_MS = 24 * 3600 * 1000;

function postedCutoff(days, now) {
  if (!days) return null;
  const ref = now instanceof Date ? now.getTime() : Number(now) || Date.now();
  return new Date(ref - days * DAY_MS).toISOString().slice(0, 10);
}

/**
 * Apply the viewer's signal set and facets. Include words: any match keeps
 * (none = everything). Exclude words: any match drops. Set facets: empty
 * means all. `ignore` names facets to skip (for a facet's own counts).
 * @param {object[]} rows
 * @param {ReturnType<typeof EMPTY_EXPLORE>} spec
 * @param {{ignore?: Set<string>, now?: Date|number}} [opts]
 */
export function filterCorpus(rows, spec = EMPTY_EXPLORE(), { ignore = new Set(), now = Date.now() } = {}) {
  const s = { ...EMPTY_EXPLORE(), ...spec };
  const set = compileSignalSet({ include: cleanWords(s.include), exclude: cleanWords(s.exclude) });
  const terms = String(s.q || '').toLowerCase().split(/\s+/).filter(Boolean);
  const on = (name, values) => !ignore.has(name) && values && values.size > 0;
  const cutoff = ignore.has('posted') ? null : postedCutoff(s.posted, now);
  return (rows || []).filter((r) => {
    if (on('tiers', s.tiers) && !s.tiers.has(r.tier)) return false;
    if (on('roles', s.roles) && !s.roles.has(r.cat)) return false;
    if (on('sources', s.sources) && !s.sources.has(r.src)) return false;
    if (on('countries', s.countries) && !s.countries.has(r.country)) return false;
    if (cutoff && (!r.posted || r.posted < cutoff)) return false;
    if (!ignore.has('words') && !set.test(r.title)) return false;
    return terms.every((t) => r.hay.includes(t));
  });
}

/** [value, count] pairs for `key` over the rows, most first (ties by value). */
export function countBy(rows, key) {
  const m = new Map();
  for (const r of rows || []) {
    const k = key(r);
    if (k) m.set(k, (m.get(k) || 0) + 1);
  }
  return [...m].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
}

/** Counts for one facet, computed without that facet applied so its chips stay switchable. */
export function facetCounts(rows, spec, facet, key, opts = {}) {
  return countBy(filterCorpus(rows, spec, { ...opts, ignore: new Set([facet]) }), key);
}

/** [tierKey, count] for every tier, zeros kept, in TIERS order. */
export function tierCounts(rows) {
  const counts = new Map(countBy(rows, (r) => r.tier));
  return TIER_KEYS.map((k) => [k, counts.get(k) || 0]);
}

/** Which of the viewer's include words hit this title (for the detail pane). */
export function matchedWords(title, include) {
  return cleanWords(include).filter((w) => matchesAny(title, compileSignals([w], TRACK_SUFFIX)));
}

export const tierInfo = (key) => TIER_BY_KEY.get(key) || TIER_BY_KEY.get('out');

/** Newest first (undated last), then company and title; never mutates. */
export function sortNewest(rows) {
  return [...(rows || [])].sort((a, b) => (b.posted || '').localeCompare(a.posted || '') || a.co.localeCompare(b.co) || a.title.localeCompare(b.title));
}

const CSV_HEADER = ['company', 'title', 'location', 'source', 'posted', 'category', 'tier', 'url'];
const csvCell = (v) => {
  const s = String(v ?? '');
  // Neutralise spreadsheet formula injection, then quote.
  const safe = /^[=+\-@\t\r]/.test(s) ? `'${s}` : s;
  return `"${safe.replace(/"/g, '""')}"`;
};

/** CSV of the given rows (RFC 4180 quoting, formula-safe). */
export function toCsv(rows) {
  const lines = [CSV_HEADER.join(',')];
  for (const r of rows || []) {
    lines.push([r.co, r.title, r.loc, r.src, r.posted, r.cat, r.tier, r.url].map(csvCell).join(','));
  }
  return `${lines.join('\r\n')}\r\n`;
}
