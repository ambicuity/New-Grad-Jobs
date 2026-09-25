import { useEffect, useState } from 'react';
import { formatLiveStamp, liveStampState } from '../../lib/live-stamp.js';

const TICK_MS = 30 * 1000;

function ago(ms) {
  const m = Math.round(ms / 60000);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 48 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
}

/**
 * LIVE / STALE / OFFLINE word for the top bar (colour carries the state, the
 * tooltip carries the age). Re-renders every 30s so it moves to STALE if the
 * scraper stops updating.
 * @param {{generatedAt?: string}} props  jobs meta.generated_at
 */
export function LiveStamp({ generatedAt }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(id);
  }, []);
  const stamp = formatLiveStamp(generatedAt, now);
  const state = liveStampState(generatedAt, now);
  const title = state.kind === 'offline' ? 'no feed timestamp' : `data generated ${ago(state.ageMs)}`;
  return <span title={title} aria-label={`feed ${stamp.label.toLowerCase()}, ${title}`} style={{ color: stamp.dot, fontWeight: 600, letterSpacing: 0.8 }}>{stamp.label}</span>;
}
