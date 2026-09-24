// Escaping and text helpers for the build-time SEO generator. Every value that
// reaches generated HTML/XML/JSON-LD comes from scraped job data, so nothing is
// interpolated without going through one of these.

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

/** Entity-escape for HTML text and attribute values (also valid XML). */
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => HTML_ESCAPES[ch]);
}

/**
 * JSON for embedding inside <script type="application/ld+json">. `<`, `>` and
 * `&` become \u escapes so a value containing `</script>` or `<!--` can never
 * terminate or alter the block; U+2028/2029 are escaped for old JS parsers.
 */
const LINE_SEP = new RegExp(String.fromCharCode(0x2028), "g");
const PARA_SEP = new RegExp(String.fromCharCode(0x2029), "g");

export function jsonForScript(value) {
  return JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(LINE_SEP, '\\u2028')
    .replace(PARA_SEP, '\\u2029');
}

const NAMED_ENTITIES = {
  nbsp: ' ', amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", mdash: '—', ndash: '–',
  hellip: '…', rsquo: '’', lsquo: '‘', rdquo: '”', ldquo: '“', bull: '•', middot: '·',
};

/**
 * Scraped descriptions are plain text that still carries HTML entities
 * (`&nbsp;`, `&amp;`, …). Decode them once so re-escaping doesn't render
 * "&amp;amp;". Unknown named entities are left as-is (and escaped later).
 */
export function decodeEntities(text) {
  return String(text ?? '').replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (whole, body) => {
    if (body[0] === '#') {
      const code = body[1] === 'x' || body[1] === 'X' ? parseInt(body.slice(2), 16) : parseInt(body.slice(1), 10);
      return Number.isFinite(code) && code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : whole;
    }
    const named = NAMED_ENTITIES[body.toLowerCase()];
    return named ?? whole;
  });
}

/** Decoded, tag-free, whitespace-collapsed text. */
export function cleanText(text) {
  return decodeEntities(String(text ?? '').replace(/<[^>]*>/g, ' '))
    .replace(/\s+/g, ' ')
    .trim();
}

const PARAGRAPH_TARGET_CHARS = 600;

/**
 * Split a single-line description into readable paragraphs at sentence
 * boundaries (~600 chars each). Pure text in, text out — escape afterwards.
 */
export function toParagraphs(text) {
  const clean = cleanText(text);
  if (!clean) return [];
  const sentences = clean.match(/[^.!?]+(?:[.!?]+["”’)]*|$)\s*/g) || [clean];
  const out = [];
  let buf = '';
  for (const s of sentences) {
    buf += s;
    if (buf.length >= PARAGRAPH_TARGET_CHARS) {
      out.push(buf.trim());
      buf = '';
    }
  }
  if (buf.trim()) out.push(buf.trim());
  return out;
}

/** First `max` chars of `text` on a word boundary, with an ellipsis when cut. */
export function truncate(text, max) {
  const clean = cleanText(text);
  if (clean.length <= max) return clean;
  const cut = clean.slice(0, max - 1);
  const lastSpace = cut.lastIndexOf(' ');
  return `${(lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd()}…`;
}
