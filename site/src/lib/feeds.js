// Which RSS feed matches the current filters. The scraper publishes feed.xml
// (everything) plus feeds/<slug>.xml slices: one per category, `remote` and
// `no-visa-restriction` (scripts/ngj/outputs/rss.py). A single-facet view maps
// to its slice; anything more specific falls back to the full feed.

import { CATEGORY_TYPE } from './taxonomy.js';

export const MAIN_FEED = 'feed.xml';
export const FEEDS_DIR = 'feeds';

const TYPE_TO_CATEGORY = Object.fromEntries(Object.entries(CATEGORY_TYPE).map(([id, code]) => [code, id]));

/** `software_engineering` → `feeds/software-engineering.xml`. */
export function categoryFeedPath(categoryId) {
  if (typeof categoryId !== 'string' || !categoryId || categoryId === 'other') return MAIN_FEED;
  return `${FEEDS_DIR}/${categoryId.replace(/_/g, '-')}.xml`;
}

/**
 * Relative path of the feed that best matches `filters`
 * (see lib/filters.js JobFilters). Only one facet may be active for a slice.
 * @returns {string}
 */
export function feedPathFor(filters) {
  if (!filters) return MAIN_FEED;
  const types = filters.type instanceof Set ? filters.type : new Set();
  const rmt = filters.rmt instanceof Set ? filters.rmt : new Set();
  const others = (filters.tier instanceof Set ? filters.tier.size : 0)
    + (filters.company instanceof Set ? filters.company.size : 0)
    + (filters.newWithinHours ? 1 : 0);
  const visaOnly = filters.visa === true;
  if (others > 0) return MAIN_FEED;
  if (types.size === 1 && rmt.size === 0 && filters.visa === null) {
    const [code] = types;
    const id = TYPE_TO_CATEGORY[code];
    return id && id !== 'other' ? categoryFeedPath(id) : MAIN_FEED;
  }
  if (types.size === 0 && rmt.size === 1 && rmt.has('remote') && filters.visa === null) return `${FEEDS_DIR}/remote.xml`;
  if (types.size === 0 && rmt.size === 0 && visaOnly) return `${FEEDS_DIR}/no-visa-restriction.xml`;
  return MAIN_FEED;
}

/** "Open in Feedly" for an absolute feed URL (Feedly asks the viewer to sign in; no account is needed on our side). */
export const feedlyUrl = (absoluteFeedUrl) => `https://feedly.com/i/subscription/feed/${encodeURIComponent(absoluteFeedUrl)}`;
