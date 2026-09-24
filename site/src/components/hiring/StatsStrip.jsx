import { BBG } from '../../lib/theme.js';
import { Stat } from '../ui.jsx';

/**
 * Top strip of headline numbers for the whole feed (not the filtered view).
 * Every value comes from computeStats() — see lib/stats.js.
 * @param {{stats: import('../../lib/stats.js').FeedStats, isMobile: boolean}} props
 */
export function StatsStrip({ stats, isMobile }) {
  const { comp } = stats;
  return (
    <div
      role="region"
      aria-label="Feed statistics"
      // Scrolls sideways on phones, so keyboard users must be able to focus it (WCAG 2.1.1).
      tabIndex={isMobile ? 0 : undefined}
      style={{
        display: 'flex', alignItems: 'center', borderBottom: `1px solid ${BBG.rule2}`,
        padding: '10px 14px', gap: isMobile ? 14 : 18,
        // Phones can't fit every stat side-by-side; let them scroll horizontally
        // rather than wrap or shrink below legibility.
        overflowX: isMobile ? 'auto' : 'visible',
      }}
    >
      <Stat
        label="OPEN"
        value={stats.open}
        delta={`${stats.companies} companies${stats.closed ? ` · ${stats.closed} closed` : ''}`}
      />
      <Stat label="NEW 24H" value={stats.newToday} delta="posted <24h ago" deltaC={BBG.ok} />
      <Stat
        label="MED COMP"
        value={comp.median === null ? '—' : `$${comp.median}k`}
        delta={comp.n ? `midpoint of ${comp.n} posted ranges` : 'no ranges posted'}
      />
      <Stat label="VISA" value={stats.visaClear.pct} delta="no restriction stated" />
      {!isMobile && <div style={{ marginLeft: 'auto', color: BBG.dim, fontSize: 11 }}>HIRING · live job feed</div>}
    </div>
  );
}
