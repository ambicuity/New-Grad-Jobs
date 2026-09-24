// URL hygiene for anything scraped from third-party job boards.

const SAFE_PROTOCOLS = new Set(['http:', 'https:']);

/**
 * The normalised href when `value` is an absolute http(s) URL, else ''.
 * Every job link rendered as an <a href> or opened with window.open goes
 * through this, so a `javascript:` / `data:` URL in the feed can never run.
 * @param {unknown} value
 * @returns {string}
 */
export function safeHttpUrl(value) {
  if (typeof value !== 'string') return '';
  const text = value.trim();
  if (!text) return '';
  let parsed;
  try {
    parsed = new URL(text);
  } catch {
    return '';
  }
  return SAFE_PROTOCOLS.has(parsed.protocol) ? parsed.href : '';
}
