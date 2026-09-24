// Small visual pieces of the contributors view.

import { BBG } from '../../lib/theme.js';
import { fmtK } from '../../lib/format.js';
import { avatarMonogram } from '../../lib/contributors.js';

/** Pseudo-avatar: 2-letter monogram on a hashed colour block. */
export function Avatar({ handle, size = 24 }) {
  const { hue, initials } = avatarMonogram(handle);
  return (
    <div style={{
      width: size, height: size, flexShrink: 0,
      background: `hsl(${hue} 32% 22%)`,
      color: `hsl(${hue} 70% 78%)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.42, fontWeight: 700, letterSpacing: 0.5,
      border: `1px solid hsl(${hue} 35% 32%)`,
    }}>{initials}</div>
  );
}

/** Added/deleted ratio bar with the combined LoC count. */
export function PMBar({ add, del }) {
  const total = add + del || 1;
  const aPct = (add / total) * 100;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ display: 'inline-flex', height: 6, width: 36, background: BBG.panel2 }}>
        <span style={{ width: `${aPct}%`, background: BBG.ok }} />
        <span style={{ width: `${100 - aPct}%`, background: BBG.hot, opacity: 0.7 }} />
      </span>
      <span style={{ fontSize: 10, color: BBG.dim }}>{fmtK(add + del)}</span>
    </div>
  );
}

export function Sparkline({ values }) {
  const W = 420;
  const H = 44;
  const max = Math.max(...values);
  const stepX = W / (values.length - 1);
  const pts = values.map((v, i) => `${i * stepX},${H - (v / max) * H}`).join(' ');
  const area = `0,${H} ${pts} ${W},${H}`;
  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ display: 'block' }}>
      <polygon points={area} fill={BBG.acc} opacity={0.12} />
      <polyline points={pts} fill="none" stroke={BBG.acc} strokeWidth={1.4} />
      {values.map((v, i) => (
        <circle key={i} cx={i * stepX} cy={H - (v / max) * H} r={1.4} fill={BBG.acc} />
      ))}
    </svg>
  );
}
