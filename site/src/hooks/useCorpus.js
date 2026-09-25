import { useEffect, useRef, useState } from 'react';
import { loadCorpus } from '../data/corpus-source.js';

const IDLE = Object.freeze({ rows: [], meta: {}, status: 'idle', encoding: null, error: null });
const LOADING = Object.freeze({ ...IDLE, status: 'loading' });

/**
 * The corpus for the EXPLORE tab, fetched once the first time `enabled` is
 * true and kept for the session. `status`: idle | loading | ready | error.
 */
export function useCorpus(enabled, load = loadCorpus) {
  const [result, setResult] = useState(null);
  const requested = useRef(false);
  useEffect(() => {
    if (!enabled || requested.current) return undefined;
    requested.current = true;
    let cancelled = false;
    load().then((r) => {
      if (!cancelled) setResult({ rows: r.rows, meta: r.meta, status: r.error ? 'error' : 'ready', encoding: r.encoding, error: r.error });
    });
    return () => {
      cancelled = true;
      requested.current = false;
    };
  }, [enabled, load]);
  if (result) return result;
  return enabled ? LOADING : IDLE;
}
