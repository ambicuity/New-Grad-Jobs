// Full "About the role" text lives in descriptions/<0-f>.json, keyed by
// job_id and sharded on the first hex digit after the `job_` prefix. This
// mirrors scripts/publish.py `description_shard()` exactly — keep them in step.

export const DESCRIPTION_SHARD_KEYS = '0123456789abcdef'.split('');
const JOB_ID_PREFIX = 'job_';

/**
 * Shard key ('0'-'f') for a `job_<hex>` id, or null when the id can't be
 * sharded (publish.py raises for the same inputs).
 * @param {unknown} jobId
 * @returns {string|null}
 */
export function descriptionShard(jobId) {
  if (typeof jobId !== 'string' || !jobId.startsWith(JOB_ID_PREFIX)) return null;
  const key = jobId.slice(JOB_ID_PREFIX.length, JOB_ID_PREFIX.length + 1).toLowerCase();
  return DESCRIPTION_SHARD_KEYS.includes(key) ? key : null;
}

/** Relative URL of a shard (relative so the site also works under a sub-path). */
export function descriptionShardUrl(key) {
  return `./descriptions/${key}.json`;
}

const NAMED_ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
const ENTITY_RE = /&(?:#(\d{1,7})|#x([0-9a-f]{1,6})|([a-z]+));/gi;
const MAX_CODE_POINT = 0x10ffff;

function decodeEntity(match, dec, hex, name) {
  if (name) return Object.hasOwn(NAMED_ENTITIES, name.toLowerCase()) ? NAMED_ENTITIES[name.toLowerCase()] : match;
  const code = dec ? parseInt(dec, 10) : parseInt(hex, 16);
  return code > 0 && code <= MAX_CODE_POINT ? String.fromCodePoint(code) : match;
}

/**
 * Scraped descriptions are plain text that still carries HTML entities
 * (`&amp;`, `&nbsp;`, `&#39;`). Decode them in a single pass for display as
 * text (React escapes the result, so nothing here is ever parsed as HTML).
 * @param {string} text
 */
export function cleanDescription(text) {
  return text.replace(ENTITY_RE, decodeEntity).trim();
}

/**
 * Description text for `jobId` from a loaded shard, or null if absent.
 * @param {Record<string, unknown>|null|undefined} shard
 * @param {string} jobId
 */
export function lookupDescription(shard, jobId) {
  if (!shard || typeof shard !== 'object') return null;
  const text = shard[jobId];
  return typeof text === 'string' ? text : null;
}
