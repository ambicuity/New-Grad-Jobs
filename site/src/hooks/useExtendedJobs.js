import { useEffect, useRef, useState } from 'react';
import { loadExtendedJobs } from '../data/jobs-source.js';

const IDLE = Object.freeze({ jobs: [], status: 'idle' });
const LOADING = Object.freeze({ jobs: [], status: 'loading' });

/**
 * The near-miss tier, fetched once the first time `enabled` is true and kept
 * afterwards. `status` is idle | loading | ready | error; `jobs` is [] until
 * ready, so the board never blocks on it.
 * @returns {{jobs: import('../lib/jobs.js').Job[], status: string}}
 */
export function useExtendedJobs(enabled, load = loadExtendedJobs) {
  const [result, setResult] = useState(null);
  const requested = useRef(false);
  useEffect(() => {
    if (!enabled || requested.current) return undefined;
    requested.current = true;
    let cancelled = false;
    load().then((r) => {
      if (!cancelled) setResult({ jobs: r.jobs, status: r.error ? 'error' : 'ready' });
    });
    return () => {
      cancelled = true;
      requested.current = false;
    };
  }, [enabled, load]);
  if (result) return result;
  return enabled ? LOADING : IDLE;
}
