// Left rail of the hiring view: facet chips, deadline histogram and the
// HIRING NOW company list (which doubles as the company facet).

import { useMemo } from 'react';
import { BBG } from '../../lib/theme.js';
import { RMT_ORDER, SIZE_LABEL, SIZE_ORDER, TYPE_LABEL, TYPE_ORDER } from '../../lib/taxonomy.js';
import { activeFilterCount, companyCounts, deadlineBuckets } from '../../lib/filters.js';
import { Chip, ChipGroup, DrawerToggle, onActivateKey, sectionLabel } from '../ui.jsx';

export function FilterRail({
  isMobile, open, onToggleOpen, filters, onToggle, onVisa, filtered, preCompanyFiltered,
}) {
  return (
    <div style={{
      borderRight: isMobile ? 'none' : `1px solid ${BBG.rule2}`,
      borderBottom: isMobile ? `1px solid ${BBG.rule2}` : 'none',
      overflow: isMobile ? 'visible' : 'auto',
    }}>
      {isMobile && (
        <DrawerToggle open={open} onToggle={onToggleOpen} label="FILTERS" activeCount={activeFilterCount(filters)} />
      )}
      {(!isMobile || open) && (
        <>
          <ChipGroup title="ROLE">
            {TYPE_ORDER.map((t) => (
              <Chip key={t} on={filters.type.has(t)} onClick={() => onToggle('type', t)} label={TYPE_LABEL[t]} />
            ))}
          </ChipGroup>
          <ChipGroup title="REMOTE">
            {RMT_ORDER.map((r) => (
              <Chip key={r} on={filters.rmt.has(r)} onClick={() => onToggle('rmt', r)} label={r} />
            ))}
          </ChipGroup>
          <ChipGroup title="VISA">
            <Chip on={filters.visa === true} onClick={() => onVisa(true)} label="sponsored" />
            <Chip on={filters.visa === false} onClick={() => onVisa(false)} label="us-only" />
          </ChipGroup>
          <ChipGroup title="COHORT">
            <Chip on={filters.cohort.has('26')} onClick={() => onToggle('cohort', '26')} label="'26" />
            <Chip on={filters.cohort.has('25')} onClick={() => onToggle('cohort', '25')} label="'25" />
          </ChipGroup>
          <ChipGroup title="COMPANY SIZE">
            {SIZE_ORDER.map((s) => (
              <Chip key={s} on={filters.size.has(s)} onClick={() => onToggle('size', s)} label={SIZE_LABEL[s]} />
            ))}
          </ChipGroup>
          <DeadlineDist jobs={filtered} />
          <HiringNow jobs={preCompanyFiltered} selected={filters.company} onToggle={(co) => onToggle('company', co)} />
        </>
      )}
    </div>
  );
}

function DeadlineDist({ jobs }) {
  const b = useMemo(() => deadlineBuckets(jobs), [jobs]);
  const rows = [
    ['<7d', b.w1, BBG.hot],
    ['<14d', b.w2, BBG.warn],
    ['<1mo', b.m1, BBG.acc],
    ['<3mo', b.m3, BBG.ok],
    ['>3mo', b.m3p, BBG.dim],
  ];
  return (
    <div style={{ padding: '12px 14px', borderTop: `1px solid ${BBG.rule}`, marginTop: 6 }}>
      <div style={sectionLabel}>DEADLINE DIST.</div>
      {rows.map(([lbl, n, c]) => (
        <div key={lbl} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, marginBottom: 2 }}>
          <span style={{ width: 32, color: BBG.dim }}>{lbl}</span>
          <div style={{ flex: 1, height: 6, background: BBG.panel2, position: 'relative' }}>
            <div style={{ position: 'absolute', inset: 0, width: `${Math.min(100, (n / (jobs.length || 1)) * 100)}%`, background: c }} />
          </div>
          <span style={{ width: 22, textAlign: 'right' }}>{n}</span>
        </div>
      ))}
    </div>
  );
}

function HiringNow({ jobs, selected, onToggle }) {
  const counts = useMemo(() => companyCounts(jobs), [jobs]);
  return (
    <div style={{ padding: '12px 14px', borderTop: `1px solid ${BBG.rule}` }}>
      <div style={{ ...sectionLabel, display: 'flex', justifyContent: 'space-between' }}>
        <span>HIRING NOW</span>
        <span style={{ color: BBG.acc }}>{counts.length}</span>
      </div>
      <div style={{ maxHeight: 220, overflowY: 'auto' }}>
        {counts.map(([co, n]) => {
          const active = selected.has(co);
          return (
            <div
              key={co}
              role="button"
              tabIndex={0}
              aria-pressed={active}
              title={active ? `clear filter: ${co}` : `filter to ${co}`}
              onClick={() => onToggle(co)}
              onKeyDown={onActivateKey(() => onToggle(co))}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                fontSize: 11, padding: '1px 4px', cursor: 'pointer',
                background: active ? BBG.panel2 : 'transparent',
                borderLeft: `2px solid ${active ? BBG.acc : 'transparent'}`,
              }}
            >
              <span style={{ color: active ? BBG.acc : BBG.ink }}>{co}</span>
              <span style={{ color: BBG.acc }}>{n}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
