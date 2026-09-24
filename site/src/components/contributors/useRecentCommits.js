import { useCallback, useEffect, useSyncExternalStore } from 'react';
import { LOADING, recentCommitsStore } from '../../data/recent-commits.js';

// Selection can move quickly (clicking / arrowing through rows); only fetch
// once it has settled on one contributor for this long.
export const RECENT_COMMITS_DEBOUNCE_MS = 400;

/**
 * Recent commits by `handle` in this repo (shared cache). The request starts
 * only after `handle` has been shown for RECENT_COMMITS_DEBOUNCE_MS, so it
 * fires for the contributor whose detail is actually open.
 */
export function useRecentCommits(handle, { store = recentCommitsStore, delayMs = RECENT_COMMITS_DEBOUNCE_MS } = {}) {
  useEffect(() => {
    if (!handle) return undefined;
    const timer = setTimeout(() => store.ensure(handle), delayMs);
    return () => clearTimeout(timer);
  }, [handle, store, delayMs]);

  const subscribe = useCallback(
    (cb) => (handle ? store.subscribe(handle, cb) : () => {}),
    [handle, store],
  );
  const getSnapshot = useCallback(() => (handle ? store.get(handle) : LOADING), [handle, store]);
  return useSyncExternalStore(subscribe, getSnapshot);
}
