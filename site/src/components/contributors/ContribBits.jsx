// Small visual pieces of the contributors view.

import { BBG } from '../../lib/theme.js';
import { avatarMonogram } from '../../lib/contributors.js';

/** Pseudo-avatar: 2-letter monogram on a hashed colour block. */
export function Avatar({ handle, size = 24 }) {
  const { hue, initials } = avatarMonogram(handle);
  return (
    <div aria-hidden="true" style={{
      width: size, height: size, flexShrink: 0,
      background: `hsl(${hue} 32% 22%)`,
      color: `hsl(${hue} 70% 78%)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.42, fontWeight: 700, letterSpacing: 0.5,
      border: `1px solid hsl(${hue} 35% 32%)`,
    }}>{initials}</div>
  );
}

/** Contribution-type tags (all-contributors types: code, doc, test, …). */
export function TypeTags({ types, max = Infinity, size = 9.5 }) {
  if (!types.length) return <span style={{ color: BBG.dim, fontSize: size }}>—</span>;
  return (
    <span style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', overflow: 'hidden' }}>
      {types.slice(0, max).map((t) => (
        <span key={t} style={{ fontSize: size, color: BBG.dim }}>{t}</span>
      ))}
    </span>
  );
}

/** Commit count, or "—" when the GitHub API didn't give one. */
export const fmtCommits = (n) => (typeof n === 'number' ? n.toLocaleString() : '—');
