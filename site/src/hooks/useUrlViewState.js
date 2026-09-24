import { useCallback, useEffect, useRef, useState } from 'react';
import { TAB_IDS, parseViewState, serializeViewState } from '../lib/url-state.js';

// Filter / search / sort / selection changes rewrite the URL with
// replaceState, debounced so held-down j/k or fast typing doesn't hammer the
// History API (Safari throttles it). Opening something the user should be
// able to "back" out of (a mobile job detail, a tab) pushes a new entry.
export const URL_WRITE_DELAY_MS = 150;

const readLocation = () => parseViewState(window.location.search, window.location.hash);

function urlFor(view) {
  const { pathname, search, hash } = window.location;
  // Legacy #contributors / #hiring links are folded into ?tab= and dropped.
  const keepHash = TAB_IDS.includes(hash.slice(1)) ? '' : hash;
  return `${pathname}${serializeViewState(view, search)}${keepHash}`;
}

const currentUrl = () => `${window.location.pathname}${window.location.search}${window.location.hash}`;

/**
 * App-wide view state mirrored into the query string.
 * `update(fnOrPatch, {push, state})`: `push` adds a history entry (with the
 * optional `state` object) instead of replacing the current one.
 * @returns {[import('../lib/url-state.js').ViewState, (fn: object|Function, opts?: {push?: boolean, state?: object}) => void]}
 */
export function useUrlViewState() {
  const [view, setView] = useState(readLocation);
  const pending = useRef(null); // { url, timer } for a debounced replaceState
  const pushNext = useRef(null); // history state for the next write, when it must push

  const flush = useCallback(() => {
    if (!pending.current) return;
    clearTimeout(pending.current.timer);
    window.history.replaceState(window.history.state, '', pending.current.url);
    pending.current = null;
  }, []);

  const cancel = useCallback(() => {
    if (pending.current) clearTimeout(pending.current.timer);
    pending.current = null;
  }, []);

  const update = useCallback((fn, { push = false, state = null } = {}) => {
    if (push) pushNext.current = state || {};
    setView((prev) => (typeof fn === 'function' ? fn(prev) : { ...prev, ...fn }));
  }, []);

  useEffect(() => {
    const url = urlFor(view);
    cancel();
    if (pushNext.current) {
      const state = pushNext.current;
      pushNext.current = null;
      if (url !== currentUrl()) window.history.pushState(state, '', url);
      return;
    }
    if (url === currentUrl()) return;
    pending.current = {
      url,
      timer: setTimeout(() => { pending.current = null; window.history.replaceState(window.history.state, '', url); }, URL_WRITE_DELAY_MS),
    };
  }, [view, cancel]);

  useEffect(() => {
    const onPop = () => { cancel(); setView(readLocation()); };
    // A reload/close inside the debounce window must not lose the last change.
    window.addEventListener('popstate', onPop);
    window.addEventListener('pagehide', flush);
    return () => {
      window.removeEventListener('popstate', onPop);
      window.removeEventListener('pagehide', flush);
      flush();
    };
  }, [cancel, flush]);

  return [view, update];
}
