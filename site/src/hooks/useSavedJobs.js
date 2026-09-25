import { useCallback, useEffect, useState } from 'react';
import { toggleInSet } from '../lib/filters.js';
import { SAVED_STORAGE_KEY, loadSavedIds, parseSavedIds, storeSavedIds } from '../lib/saved.js';

const browserStorage = () => window.localStorage;

/**
 * Saved job ids (stable job_id), persisted to localStorage and kept in sync
 * across tabs. Works in memory when storage is unavailable. Pass
 * APPLIED_STORAGE_KEY as `key` for the "applied" list (same rules).
 * @returns {[Set<string>, (id: string) => void]}
 */
export function useSavedJobs(getStorage = browserStorage, key = SAVED_STORAGE_KEY) {
  const [saved, setSaved] = useState(() => loadSavedIds(getStorage, key));

  useEffect(() => {
    storeSavedIds(getStorage, saved, key);
  }, [getStorage, saved, key]);

  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === key) setSaved(parseSavedIds(e.newValue));
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [key]);

  const toggle = useCallback((id) => setSaved((s) => toggleInSet(s, id)), []);
  return [saved, toggle];
}
