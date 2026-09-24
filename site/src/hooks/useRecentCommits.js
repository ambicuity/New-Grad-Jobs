import { useCallback, useEffect, useSyncExternalStore } from 'react';
import { recentCommitsStore } from '../data/recent-commits.js';

const LOADING = { state: 'loading', commits: [] };

/** Recent commits by `handle` in this repo (shared session cache). */
export function useRecentCommits(handle, store = recentCommitsStore) {
  useEffect(() => {
    if (handle) store.ensure(handle);
  }, [handle, store]);

  const subscribe = useCallback(
    (cb) => (handle ? store.subscribe(handle, cb) : () => {}),
    [handle, store],
  );
  const getSnapshot = useCallback(() => (handle ? store.get(handle) : LOADING), [handle, store]);
  return useSyncExternalStore(subscribe, getSnapshot);
}
