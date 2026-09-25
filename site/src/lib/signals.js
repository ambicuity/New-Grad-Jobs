// A faithful port of the scraper's title-signal matcher (scripts/ngj/filters.py:
// _signal_pattern / _compile_signals / _compile_exclusion_pattern) so a
// viewer-defined signal in the browser means exactly what the same words mean
// in config.yml. Parity is enforced by test/fixtures/signal-parity.json,
// generated from the Python implementation by scripts/export_signal_parity.py.
//
// Rules (all case-insensitive, matched at token boundaries, never substrings):
//   * a trailing level token ("I", "sde ii", "l3") uses level-token boundaries,
//     so "Engineer I" matches and "Alvin I. Goodman" / "L3Harris" do not;
//   * a bare number ("2026") never matches inside a longer number or a req id;
//   * anything else is whole words; `suffix` allows inflections
//     ("engineer" also matches "Engineering", "Developers").

const WORD = '[\\p{L}\\p{N}_]'; // Python's Unicode-aware \w
const LEVEL_TOKEN = /^(?:[ivx]+|[le]\d)$/i;
const LEVEL_LEFT = '(?<=[\\s(\\-,\\[])';
const LEVEL_RIGHT = '(?=$|[\\s),\\-|:;\\]]|/(?:[ivx]+|[le]\\d)\\b)';
const CJK_START = 0x2e80;
const ALNUM = /^[\p{L}\p{N}]/u;
const ALPHA_END = /[\p{L}]$/u;
const ALNUM_END = /[\p{L}\p{N}]$/u;

/** Inflections a track word may carry ("engineer" → "engineering", "developers"). */
export const TRACK_SUFFIX = '(?:s|es|ing|ings|ers?|ed)?';

// Escapes only what needs it; "\-" and "\/" are invalid escapes under the u flag.
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Regex source for one signal, or null for a blank one.
 * @param {string} raw
 * @param {string} [suffix]
 */
export function signalPattern(raw, suffix = '') {
  const words = String(raw ?? '').trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return null;
  let body = words.map(escapeRe).join('\\s+');
  const last = words[words.length - 1];
  if (LEVEL_TOKEN.test(last)) {
    const left = words.length === 1 ? LEVEL_LEFT : `(?<!${WORD})`;
    return `${left}${body}${LEVEL_RIGHT}`;
  }
  if (words.length === 1 && /^\d+$/.test(words[0])) {
    return `(?<![${WORD.slice(1, -1)}#])${body}(?!${WORD}|-\\d)`;
  }
  if (suffix && [...words.join('')].every((ch) => ch.codePointAt(0) >= CJK_START)) return body;
  if (ALPHA_END.test(last)) body += suffix;
  const left = ALNUM.test(words[0]) ? `(?<!${WORD})` : '';
  const right = ALNUM_END.test(last) ? `(?!${WORD})` : '';
  return `${left}${body}${right}`;
}

/**
 * One regex for a list of signals (null when none is usable).
 * @param {Iterable<string>} signals
 * @param {string} [suffix]
 */
export function compileSignals(signals, suffix = '') {
  const parts = [...(signals || [])].map((s) => (typeof s === 'string' ? signalPattern(s, suffix) : null)).filter(Boolean);
  return parts.length ? new RegExp(parts.join('|'), 'iu') : null;
}

/** Whether `title` carries any of the compiled signals. */
export function matchesAny(title, compiled) {
  return typeof title === 'string' && Boolean(compiled) && compiled.test(title);
}

// Exclusion words behave slightly differently in the scraper (plural "s",
// longer inflections for "intern", boundaries only on alphanumeric edges).
const EXCLUSION_SUFFIXES = { intern: '(?:s|ships?)?' };

/**
 * Regex for the scraper's exclusion / internship lists (senior, staff, intern, …).
 * @param {Iterable<string>} signals
 */
export function compileExclusions(signals) {
  const parts = [];
  for (const raw of signals || []) {
    if (typeof raw !== 'string') continue;
    const core = raw.trim().toLowerCase();
    if (!core) continue;
    let body = core.split(/\s+/).map(escapeRe).join('\\s+');
    if (/[\p{L}]$/u.test(core)) body += EXCLUSION_SUFFIXES[core] || 's?';
    const left = ALNUM.test(core) ? '(?<![a-z0-9])' : '';
    const right = ALNUM_END.test(core) ? '(?![a-z0-9])' : '';
    parts.push(`${left}${body}${right}`);
  }
  return parts.length ? new RegExp(parts.join('|'), 'iu') : null;
}

// Entry-level titles that contain an exclusion word but are not senior roles
// ("Associate Product Manager"); removed before the exclusion words are
// checked, exactly as the scraper does (_EXCLUSION_EXCEPTIONS_RE).
const EXCLUSION_EXCEPTIONS = /\bassociate\s+(?:technical\s+)?(?:product|program|project)\s+managers?\b/giu;

/** Whether `title` carries an exclusion word, honouring the APM/TPM exception. */
export function isTitleExcluded(title, compiled) {
  if (typeof title !== 'string' || !title || !compiled) return false;
  return matchesAny(title.replace(EXCLUSION_EXCEPTIONS, ' '), compiled);
}

/**
 * A viewer-defined signal set: keep a title when it matches any `include`
 * word and none of the `exclude` words. Compiled once, applied per title.
 * @param {{include?: string[], exclude?: string[]}} spec
 */
export function compileSignalSet(spec) {
  const include = compileSignals((spec && spec.include) || [], TRACK_SUFFIX);
  const exclude = compileExclusions((spec && spec.exclude) || []);
  return {
    include,
    exclude,
    test: (title) => (include ? matchesAny(title, include) : true) && !isTitleExcluded(title, exclude),
  };
}
