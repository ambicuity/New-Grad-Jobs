// Lazily loads description shards. One shard is fetched the first time a job
// in it is opened, then served from memory; a failed fetch is evicted so the
// next open retries.

import { descriptionShardUrl } from '../lib/descriptions.js';

export function createShardLoader(fetchImpl = (...args) => fetch(...args)) {
  const cache = new Map(); // shard key → Promise<Record<string, string>>
  return function loadShard(key) {
    if (!cache.has(key)) {
      const url = descriptionShardUrl(key);
      const p = fetchImpl(url, { cache: 'no-cache' })
        .then((r) => {
          if (!r.ok) throw new Error(`descriptions/${key}.json: HTTP ${r.status}`);
          return r.json();
        })
        .catch((err) => {
          console.error('[terminal] description shard failed:', err);
          cache.delete(key);
          return {};
        });
      cache.set(key, p);
    }
    return cache.get(key);
  };
}

export const loadDescriptionShard = createShardLoader();
