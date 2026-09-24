// Per-contributor recent commits from the GitHub API, cached for the session
// and shared between every component that shows the same handle.

import { REPO_SLUG, mapRecentCommits } from '../lib/contributors.js';
import { formatAgo } from '../lib/time.js';

const RECENT_LIMIT = 4;
// Stable reference: useSyncExternalStore requires snapshots to be referentially stable.
const LOADING = Object.freeze({ state: 'loading', commits: [] });

/**
 * @typedef {{state: 'loading'|'ok'|'empty'|'error', commits: {sha: string, msg: string, ago: string, url: string}[], error?: string}} RecentCommitsEntry
 */

export function createRecentCommitsStore(fetchImpl = (...args) => fetch(...args)) {
  /** @type {Map<string, RecentCommitsEntry>} */
  const cache = new Map();
  const listeners = new Map(); // handle → Set<() => void>

  const notify = (handle) => (listeners.get(handle) || new Set()).forEach((cb) => cb());

  async function fetchCommits(handle) {
    const url = `https://api.github.com/repos/${REPO_SLUG}/commits?author=${encodeURIComponent(handle)}&per_page=${RECENT_LIMIT}`;
    const resp = await fetchImpl(url, { headers: { Accept: 'application/vnd.github+json' } });
    if (!resp.ok) throw new Error(`gh api ${resp.status}`);
    return mapRecentCommits(await resp.json(), formatAgo);
  }

  function ensure(handle) {
    if (cache.has(handle)) return;
    cache.set(handle, LOADING);
    fetchCommits(handle)
      .then((commits) => cache.set(handle, { state: commits.length ? 'ok' : 'empty', commits }))
      .catch((err) => cache.set(handle, { state: 'error', commits: [], error: String((err && err.message) || err) }))
      .finally(() => notify(handle));
  }

  function subscribe(handle, cb) {
    const set = listeners.get(handle) || new Set();
    set.add(cb);
    listeners.set(handle, set);
    return () => {
      set.delete(cb);
      if (!set.size) listeners.delete(handle);
    };
  }

  /** @returns {RecentCommitsEntry} */
  function get(handle) {
    return cache.get(handle) || LOADING;
  }

  return { ensure, subscribe, get };
}

export const recentCommitsStore = createRecentCommitsStore();
