import { useMemo } from 'react';
import { BBG } from '../../lib/theme.js';
import { pct } from '../../lib/format.js';
import { closingSoonCount, newTodayCount } from '../../lib/filters.js';
import { Stat } from '../ui.jsx';

/** Top strip of headline numbers for the whole feed (not the filtered view). */
export function StatsStrip({ jobs, isMobile }) {
  const stats = useMemo(() => ({
    newToday: newTodayCount(jobs),
    closing: closingSoonCount(jobs),
    visa: pct(jobs.filter((j) => j.visa).length, jobs.length),
  }), [jobs]);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', borderBottom: `1px solid ${BBG.rule2}`,
      padding: '10px 14px', gap: isMobile ? 14 : 18,
      // Phones can't fit 5 stats side-by-side; let them scroll horizontally
      // rather than wrap or shrink below legibility.
      overflowX: isMobile ? 'auto' : 'visible',
    }}>
      <Stat label="OPEN" value={jobs.length} delta="+12 24h" deltaC={BBG.ok} />
      <Stat label="NEW TODAY" value={stats.newToday} delta="+5" deltaC={BBG.ok} />
      <Stat label="CLOSING <7d" value={stats.closing} delta="⚠" deltaC={BBG.hot} />
      <Stat label="MED COMP" value="$170k" delta="+2.1%" deltaC={BBG.ok} />
      <Stat label="VISA✓" value={stats.visa} delta="" deltaC={BBG.dim} />
      {!isMobile && <div style={{ marginLeft: 'auto', color: BBG.dim, fontSize: 11 }}>HIRING · live job feed</div>}
    </div>
  );
}
