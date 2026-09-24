// Small presentational building blocks shared by the hiring and contributors views.

import { BBG } from '../lib/theme.js';

export const sectionLabel = { color: BBG.dim, fontSize: 10, letterSpacing: 0.7, marginBottom: 6 };
export const ellipsis = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' };

export function Stat({ label, value, delta, deltaC }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 56, flexShrink: 0 }}>
      <span style={{ fontSize: 9.5, color: BBG.dim, letterSpacing: 0.8 }}>{label}</span>
      <span style={{ fontSize: 14, color: BBG.ink, fontWeight: 600, lineHeight: 1.15 }}>{value}</span>
      {delta && <span style={{ fontSize: 9.5, color: deltaC || BBG.dim }}>{delta}</span>}
    </div>
  );
}

export function ChipGroup({ title, children }) {
  return (
    <div style={{ padding: '10px 14px', borderBottom: `1px solid ${BBG.rule}` }}>
      <div style={sectionLabel}>{title}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>{children}</div>
    </div>
  );
}

/**
 * Toggle chip. `dot` (contributors AREA chips) shows a colour swatch while off;
 * `flex` lays the chip out as inline-flex (the contributors chip style).
 */
export function Chip({ on, onClick, label, dot, flex = false }) {
  return (
    <button onClick={onClick} aria-pressed={on} style={{
      background: on ? BBG.acc : 'transparent',
      color: on ? '#000' : BBG.ink,
      border: `1px solid ${on ? BBG.acc : BBG.rule2}`,
      padding: '2px 7px', fontFamily: 'inherit', fontSize: 11, cursor: 'pointer',
      letterSpacing: 0.2, fontWeight: on ? 600 : 400,
      ...(flex || dot ? { display: 'inline-flex', alignItems: 'center', gap: 4 } : null),
    }}>
      {dot && !on && <span style={{ display: 'inline-block', width: 5, height: 5, background: dot }} />}
      {label}
    </button>
  );
}

export function SortHeader({ k, label, cur, dir, onClick }) {
  const active = cur === k;
  return (
    <button onClick={() => onClick(k)} style={{
      background: 'transparent', border: 'none', cursor: 'pointer',
      color: active ? BBG.acc : BBG.dim, fontFamily: 'inherit', fontSize: 10, letterSpacing: 0.6,
      padding: 0, textAlign: 'left',
    }}>
      {label}{active ? (dir > 0 ? ' ▲' : ' ▼') : ''}
    </button>
  );
}

export function FKey({ n, l }) {
  return (
    <span><span style={{ color: BBG.acc, fontWeight: 700, marginRight: 4 }}>{n}</span>{l}</span>
  );
}

export function Metric({ label, value, sub, color, size = 18 }) {
  return (
    <div style={{ padding: '10px 14px', borderRight: `1px solid ${BBG.rule}` }}>
      <div style={{ color: BBG.dim, fontSize: 9.5, letterSpacing: 0.7 }}>{label}</div>
      <div style={{ color, fontSize: size, fontWeight: 600, marginTop: 2 }}>{value}</div>
      <div style={{ color: BBG.dim, fontSize: 10 }}>{sub}</div>
    </div>
  );
}

/** Mobile drawer toggle ("▸ FILTERS · 2 active"). */
export function DrawerToggle({ open, onToggle, label, activeCount }) {
  return (
    <button
      onClick={onToggle}
      aria-expanded={open}
      style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: 8,
        background: BBG.panel2, border: 'none', borderBottom: `1px solid ${BBG.rule2}`,
        color: BBG.ink, fontFamily: 'inherit', fontSize: 12, letterSpacing: 0.6,
        padding: '12px 14px', cursor: 'pointer', minHeight: 44, textAlign: 'left',
      }}
    >
      <span style={{ color: BBG.acc }}>{open ? '▾' : '▸'}</span>
      <span>{label}</span>
      {activeCount ? <span style={{ color: BBG.acc }}>· {activeCount} active</span> : null}
    </button>
  );
}

/** Full-screen mobile detail with a "‹ BACK" bar. */
export function MobileOverlay({ title, backLabel, onBack, children }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50, background: BBG.bg,
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        borderBottom: `1px solid ${BBG.rule2}`, background: BBG.panel,
        padding: '0 6px', minHeight: 48, flexShrink: 0,
      }}>
        <button onClick={onBack} aria-label={backLabel} style={{
          background: 'transparent', border: 'none', color: BBG.acc, cursor: 'pointer',
          fontFamily: 'inherit', fontSize: 14, fontWeight: 600, padding: '12px 10px', minHeight: 44,
        }}>‹ BACK</button>
        <span style={{ color: BBG.dim, fontSize: 12, ...ellipsis }}>{title}</span>
      </div>
      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>{children}</div>
    </div>
  );
}

/** Enter/Space activation for non-button elements with role="button". */
export function onActivateKey(handler) {
  return (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handler(e);
    }
  };
}
