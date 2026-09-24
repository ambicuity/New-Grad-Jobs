// Best-effort extraction of a requirements bullet list from a free-text (or
// HTML) job description, for the REQUIREMENTS block of the detail pane.

const MAX_ITEMS = 8;
const MIN_LEN = 10;
const MAX_LEN = 300;
const FALLBACK_SECTION_CHARS = 1000;

const REQ_HEADERS = /(?:REQUIREMENTS|QUALIFICATIONS|WHAT YOU.{0,20}NEED|MUST HAVE|MINIMUM QUALIFICATIONS|BASIC QUALIFICATIONS|WHAT WE.{0,20}LOOKING FOR|ABOUT YOU|YOU SHOULD HAVE|YOU.{0,10}BRING|IDEAL CANDIDATE|SKILLS.{0,10}REQUIRED|REQUIRED SKILLS|MINIMUM REQUIREMENTS|EDUCATION|EXPERIENCE)[:\s]*/i;
const SECTION_END = /(?:ABOUT|WHAT YOU.{0,10}DO|RESPONSIBILITIES|NICE TO HAVE|PREFERRED|BONUS|COMPENSATION|SALARY|BENEFITS|EQUAL|LOCATION|APPLY|PERKS|WHAT WE OFFER|ABOUT THE TEAM|ABOUT THE COMPANY)/i;
const ITEM_SPLIT = /(?:^|\s)[•\-*]\s*|(?:^|\s)\d+\.\s*|(?:^|\s)[a-z]\)\s*/;
const STOP_WORD = /^(?:and|or|the|a|an|is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|could|should|may|might|can|shall)$/i;

// Strip tags until nothing changes (a single pass leaves e.g. "<scr<b>ipt>" as
// "<script>"), then drop any stray angle brackets. Output is rendered as React
// text (escaped), so this is defence in depth, not the XSS boundary.
const stripTags = (s) => {
  let prev;
  let out = s;
  do {
    prev = out;
    out = out.replace(/<[^>]*>/g, ' ');
  } while (out !== prev);
  return out.replace(/[<>]/g, ' ');
};
const inRange = (s) => s.length > MIN_LEN && s.length < MAX_LEN;

function fromHeaderSection(text) {
  const headerMatch = text.match(REQ_HEADERS);
  if (!headerMatch) return [];
  const afterHeader = text.substring(headerMatch.index + headerMatch[0].length);
  const endMatch = afterHeader.match(SECTION_END);
  const section = endMatch ? afterHeader.substring(0, endMatch.index) : afterHeader.substring(0, FALLBACK_SECTION_CHARS);
  const items = section.split(ITEM_SPLIT).map((s) => s.trim()).filter((s) => inRange(s) && !STOP_WORD.test(s));
  return items.length >= 2 ? items.slice(0, MAX_ITEMS) : [];
}

function fromListItems(html) {
  const liMatches = html.match(/<li[^>]*>([\s\S]*?)<\/li>/gi);
  if (!liMatches || liMatches.length < 3) return [];
  const items = liMatches
    .map((li) => stripTags(li).replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim())
    .filter(inRange);
  return items.length >= 3 ? items.slice(0, MAX_ITEMS) : [];
}

function extractUncached(desc) {
  const text = stripTags(desc).replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
  const fromHeader = fromHeaderSection(text);
  if (fromHeader.length) return fromHeader;
  return fromListItems(desc);
}

// Descriptions run to tens of KB and the regex pass is not free, so keyboard
// j/k back-and-forth reuses results. Bounded, oldest-first eviction (Map
// iteration order is insertion order).
export const REQUIREMENTS_CACHE_SIZE = 64;
const cache = new Map();

/**
 * @param {string|null|undefined} desc
 * @returns {string[]} up to 8 requirement lines (empty when none found).
 *   Treat as read-only: repeated calls return the same cached array.
 */
export function extractRequirements(desc) {
  if (!desc) return [];
  const hit = cache.get(desc);
  if (hit) return hit;
  const items = extractUncached(desc);
  if (cache.size >= REQUIREMENTS_CACHE_SIZE) cache.delete(cache.keys().next().value);
  cache.set(desc, items);
  return items;
}
