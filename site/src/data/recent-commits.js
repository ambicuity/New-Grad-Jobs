// Per-contributor recent commits from the GitHub API, shared between every
// component that shows the same handle.
//   - in-memory per session, plus localStorage (1 h TTL, shape-validated) so a
//     reload doesn't spend the 60 req/hr unauthenticated budget again;
//   - errors are never persisted. A 403/429 rate-limit records the reset time
//     from the response headers and is not retried before it; any other error
//     is retried on the next ensure() (i.e. the next time the detail opens).

import { REPO_SLUG, isRecentCommitRows, mapRecentCommits } from '../lib/contributors.js';
import { GH_API, GH_HEADERS, readCacheEntry, storage, writeCacheEntry } from './contributors-source.js';

const RECENT_LIMIT = 4;
const CACHE_PREFIX = 'ng-terminal:gh-commits-v1:';
// Fallback wait when a rate-limit response carries no usable reset header.
const DEFAULT_RETRY_MS = 60 * 1000;
// Stable reference: useSyncExternalStore requires snapshots to be referentially stable.
export const LOADING = Object.freeze({ state: 'loading', commits: [] });

/**
 * @typedef {{sha: string, msg: string, date: string, url: string}} CommitRow
 * @typedef {{state: 'loading'|'ok'|'empty'|'error', commits: CommitRow[], error?: string, retryAt?: number}} RecentCommitsEntry
 */

/** Epoch ms after which a rate-limited request may be retried. */
export function retryAtFromHeaders(headers, now) {
  const get = (k) => (headers && typeof headers.get === 'function' ? headers.get(k) : null);
  const retryAfter = Number(get('retry-after'));
  if (Number.isFinite(retryAfter) && retryAfter > 0) return now + retryAfter * 1000;
  const reset = Number(get('x-ratelimit-reset'));
  if (Number.isFinite(reset) && reset * 1000 > now) return reset * 1000;
  return now + DEFAULT_RETRY_MS;
}

const isRateLimited = (resp) => resp.status === 429
  || (resp.status === 403 && (!resp.headers || typeof resp.headers.get !== 'function'
    || resp.headers.get('x-ratelimit-remaining') === '0' || resp.headers.get('retry-after') != null));

export function createRecentCommitsStore({
  fetchImpl = (...args) => fetch(...args),
  store = storage(),
  now = () => Date.now(),
} = {}) {
  /** @type {Map<string, RecentCommitsEntry>} */
  const cache = new Map();
  const listeners = new Map(); // handle → Set<() => void>

  const notify = (handle) => (listeners.get(handle) || new Set()).forEach((cb) => cb());
  const set = (handle, entry) => {
    cache.set(handle, entry);
    notify(handle);
  };
  const lsKey = (handle) => CACHE_PREFIX + handle.toLowerCase();
  const toEntry = (commits) => ({ state: commits.length ? 'ok' : 'empty', commits });

  async function fetchCommits(handle) {
    const url = `${GH_API}/repos/${REPO_SLUG}/commits?author=${encodeURIComponent(handle)}&per_page=${RECENT_LIMIT}`;
    let resp;
    try {
      resp = await fetchImpl(url, { headers: GH_HEADERS });
    } catch (err) {
      return { state: 'error', commits: [], error: String((err && err.message) || err || 'network') };
    }
    if (!resp.ok) {
      if (isRateLimited(resp)) {
        return { state: 'error', commits: [], error: 'github rate limit reached', retryAt: retryAtFromHeaders(resp.headers, now()) };
      }
      return { state: 'error', commits: [], error: `gh api ${resp.status}` };
    }
    try {
      const commits = mapRecentCommits(await resp.json());
      writeCacheEntry(lsKey(handle), commits, { store, now: now() });
      return toEntry(commits);
    } catch (err) {
      return { state: 'error', commits: [], error: String((err && err.message) || err) };
    }
  }

  /** Start loading `handle` unless it is loaded, in flight, or rate-limited. */
  function ensure(handle) {
    if (!handle) return;
    const current = cache.get(handle);
    if (current && current.state !== 'error') return;
    if (current && current.retryAt && now() < current.retryAt) return;
    const persisted = readCacheEntry(lsKey(handle), isRecentCommitRows, { store, now: now() });
    if (persisted) {
      set(handle, toEntry(persisted));
      return;
    }
    set(handle, LOADING);
    fetchCommits(handle).then((entry) => set(handle, entry));
  }

  function subscribe(handle, cb) {
    const subs = listeners.get(handle) || new Set();
    subs.add(cb);
    listeners.set(handle, subs);
    return () => {
      subs.delete(cb);
      if (!subs.size) listeners.delete(handle);
    };
  }

  /** @returns {RecentCommitsEntry} */
  function get(handle) {
    return cache.get(handle) || LOADING;
  }

  return { ensure, subscribe, get };
}

export const recentCommitsStore = createRecentCommitsStore();
