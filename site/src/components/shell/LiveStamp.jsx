import { useEffect, useState } from 'react';
import { formatLiveStamp } from '../../lib/live-stamp.js';

const TICK_MS = 30 * 1000;

/**
 * LIVE / STALE / OFFLINE chip for the top bar. Re-renders every 30s so the
 * badge moves from LIVE → STALE if the scraper stops updating.
 * @param {{generatedAt?: string}} props  jobs meta.generated_at
 */
export function LiveStamp({ generatedAt }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(id);
  }, []);
  const stamp = formatLiveStamp(generatedAt, now);
  return <span><span style={{ color: stamp.dot }}>●</span> {stamp.label}</span>;
}
