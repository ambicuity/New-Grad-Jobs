import { useCallback, useEffect, useState } from 'react';
import { toggleInSet } from '../lib/filters.js';
import { SAVED_STORAGE_KEY, loadSavedIds, parseSavedIds, storeSavedIds } from '../lib/saved.js';

const browserStorage = () => window.localStorage;

/**
 * Saved job ids (stable job_id), persisted to localStorage and kept in sync
 * across tabs. Works in memory when storage is unavailable.
 * @returns {[Set<string>, (id: string) => void]}
 */
export function useSavedJobs(getStorage = browserStorage) {
  const [saved, setSaved] = useState(() => loadSavedIds(getStorage));

  useEffect(() => {
    storeSavedIds(getStorage, saved);
  }, [getStorage, saved]);

  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === SAVED_STORAGE_KEY) setSaved(parseSavedIds(e.newValue));
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const toggle = useCallback((id) => setSaved((s) => toggleInSet(s, id)), []);
  return [saved, toggle];
}
