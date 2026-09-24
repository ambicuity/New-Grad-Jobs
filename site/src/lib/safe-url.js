// URL allow-listing for anything rendered as a link or opened in a new tab.
// Data comes from scraped job postings, contributors.json and the GitHub API,
// none of which we control — a `javascript:` or `data:` URL there must never
// reach an href. Shared by the app and the build-time SEO generator.

/**
 * `value` as an absolute http(s) URL string, or '' when it is anything else
 * (other schemes, relative paths, garbage, non-strings).
 * @param {unknown} value
 * @returns {string}
 */
export function safeHttpUrl(value) {
  if (typeof value !== 'string') return '';
  const trimmed = value.trim();
  if (!trimmed) return '';
  let parsed;
  try {
    parsed = new URL(trimmed);
  } catch {
    return '';
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
  return parsed.href;
}
