// Lazily loads description shards. One shard is fetched the first time a job
// in it is opened, then served from memory. A failed fetch rejects (so the
// detail pane can say "unavailable — retry") and is evicted so the retry
// actually refetches.

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
        .then((shard) => {
          if (!shard || typeof shard !== 'object' || Array.isArray(shard)) {
            throw new Error(`descriptions/${key}.json: not an object`);
          }
          return shard;
        })
        .catch((err) => {
          console.error('[terminal] description shard failed:', err);
          cache.delete(key);
          throw err;
        });
      cache.set(key, p);
    }
    return cache.get(key);
  };
}

export const loadDescriptionShard = createShardLoader();
