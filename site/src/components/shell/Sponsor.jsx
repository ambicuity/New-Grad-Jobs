import { useState } from 'react';
import { BBG } from '../../lib/theme.js';

function useHover() {
  const [hover, setHover] = useState(false);
  const on = () => setHover(true);
  const off = () => setHover(false);
  return [hover, { onMouseEnter: on, onMouseLeave: off, onFocus: on, onBlur: off }];
}

// Credit for the project's sponsor, Tailr (https://www.tailr.uk). Tailr
// supports the project, so we display its mark — the canonical white "T" on an
// ink rounded square, inlined as SVG so it renders crisply in the monochrome
// terminal with no network request. A faint stroke keeps the near-black ink
// square legible against the #000 top bar.
export function SponsoredBy() {
  const [hover, hoverProps] = useHover();
  return (
    <a
      href="https://www.tailr.uk"
      target="_blank"
      rel="noopener noreferrer"
      title="Sponsored by Tailr — tailor your résumé to each job posting"
      aria-label="Sponsored by Tailr (opens in a new tab)"
      {...hoverProps}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6, minHeight: 24,
        textDecoration: 'none',
        color: hover ? BBG.ink : BBG.dim,
        letterSpacing: 0.5,
        transition: 'color 120ms ease',
      }}
    >
      <span aria-hidden="true" style={{ fontSize: 11 }}>◆</span>
      <span style={{ fontSize: 11 }}>SPONSORED BY</span>
      <svg width="15" height="15" viewBox="0 0 64 64" aria-hidden="true" style={{ display: 'block' }}>
        <rect x="1" y="1" width="62" height="62" rx="15" fill="#1b1b1d"
          stroke="rgba(255,255,255,0.22)" strokeWidth="2" />
        <text x="32" y="47" textAnchor="middle"
          fontFamily="Georgia, 'Times New Roman', serif" fontSize="44" fill="#ffffff">T</text>
      </svg>
      <span style={{ fontWeight: 600, color: hover ? BBG.acc : BBG.ink, transition: 'color 120ms ease' }}>tailr</span>
    </a>
  );
}

export function SponsorLink() {
  const [hover, hoverProps] = useHover();
  return (
    <a
      href="https://buymeacoffee.com/ritesh.rana"
      target="_blank"
      rel="noopener noreferrer"
      title="Support the maintainer on Buy Me a Coffee"
      aria-label="Sponsor on Buy Me a Coffee (opens in a new tab)"
      {...hoverProps}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6, minHeight: 24,
        border: `1px solid ${BBG.acc}`,
        background: hover ? BBG.selBg : 'transparent',
        padding: '2px 8px',
        color: BBG.acc,
        textDecoration: 'none',
        fontWeight: 600, letterSpacing: 0.5,
        transition: 'background 120ms ease',
      }}
    >
      <span aria-hidden="true">☕</span>
      <span>SPONSOR</span>
    </a>
  );
}
