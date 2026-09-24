import { useEffect, useState } from 'react';

// Promises already seen to settle, with their value, so a remount (e.g.
// switching tabs back) renders content immediately instead of flashing the
// loading state.
const SETTLED = new WeakMap();

/**
 * Re-render once a data promise settles. The app mounts as soon as jobs are
 * in; slower sources (contributors + GitHub API) arrive later and views that
 * depend on them use this to swap their loading state for real content. A
 * rejection counts as settled (value undefined) so a view never sticks on
 * loading.
 * @template T
 * @param {Promise<T>|null|undefined} promise
 * @returns {{settled: boolean, value: T|undefined}}
 */
export function usePromiseSettled(promise) {
  const isThenable = !!promise && typeof promise.then === 'function';
  const [state, setState] = useState(() => {
    if (!isThenable) return { settled: true, value: undefined };
    if (SETTLED.has(promise)) return { settled: true, value: SETTLED.get(promise) };
    return { settled: false, value: undefined };
  });

  useEffect(() => {
    if (!isThenable) return undefined;
    let live = true;
    const done = (value) => {
      SETTLED.set(promise, value);
      if (live) setState({ settled: true, value });
    };
    promise.then(done, () => done(undefined));
    return () => { live = false; };
  }, [promise, isThenable]);

  return state;
}
