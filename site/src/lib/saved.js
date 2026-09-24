// Saved jobs persist in localStorage, keyed by the stable `job_id` (the slug
// `id` and its `#n` dedup suffix change between scrapes). Storage can be
// missing, full or blocked (private mode, sandboxed previews), so every access
// is wrapped and a broken value reads as "nothing saved".

export const SAVED_STORAGE_KEY = 'ngj:saved-jobs:v1';
export const MAX_SAVED = 2000;
const MAX_ID_LENGTH = 200;

const validId = (v) => typeof v === 'string' && v.length > 0 && v.length <= MAX_ID_LENGTH;

/**
 * @param {string|null|undefined} raw  The stored JSON.
 * @returns {Set<string>}
 */
export function parseSavedIds(raw) {
  if (typeof raw !== 'string' || !raw) return new Set();
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return new Set();
  }
  if (!Array.isArray(data)) return new Set();
  return new Set(data.filter(validId).slice(0, MAX_SAVED));
}

/** @param {Set<string>} ids */
export function serializeSavedIds(ids) {
  return JSON.stringify([...ids]);
}

/**
 * @param {() => Storage|null|undefined} getStorage  Accessing window.localStorage can itself throw.
 * @returns {Set<string>}
 */
export function loadSavedIds(getStorage) {
  try {
    const storage = getStorage();
    return storage ? parseSavedIds(storage.getItem(SAVED_STORAGE_KEY)) : new Set();
  } catch {
    return new Set();
  }
}

/**
 * @param {() => Storage|null|undefined} getStorage
 * @param {Set<string>} ids
 * @returns {boolean} false when the write could not be made (the UI keeps working in memory).
 */
export function storeSavedIds(getStorage, ids) {
  try {
    const storage = getStorage();
    if (!storage) return false;
    storage.setItem(SAVED_STORAGE_KEY, serializeSavedIds(ids));
    return true;
  } catch {
    return false;
  }
}
