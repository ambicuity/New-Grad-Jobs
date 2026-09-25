// Left rail of the hiring view: facet chips and the HIRING NOW company list
// (which doubles as the company facet). Only facets the feed actually
// publishes are offered, and only values that occur in it.

import { useMemo } from 'react';
import { BBG } from '../../lib/theme.js';
import { RMT_ORDER, TIER_LABEL, TIER_ORDER, TYPE_LABEL, TYPE_ORDER } from '../../lib/taxonomy.js';
import { activeFilterCount, companyCounts, countryCounts, metroCounts } from '../../lib/filters.js';
import { COUNTRY_FACET } from '../../lib/location.js';
import { NEAR_MISS_INFO, NEAR_MISS_REASONS, reasonCounts } from '../../lib/near-miss.js';
import { Chip, ChipGroup, DrawerToggle, MIN_TARGET, sectionLabel } from '../ui.jsx';

const MAX_METROS_LISTED = 15;

export function FilterRail({
  isMobile, open, onToggleOpen, filters, onToggle, onVisa, onClearNew, jobs, preCompanyFiltered, preLocationFiltered = preCompanyFiltered,
  extended = { jobs: [], status: 'idle' },
}) {
  const nearMissCounts = useMemo(() => new Map(reasonCounts(extended.jobs)), [extended.jobs]);
  // Countries present in the feed, as [code, label, count].
  const countries = useMemo(() => {
    const counts = new Map(countryCounts(jobs));
    return COUNTRY_FACET.filter(([code]) => counts.has(code)).map(([code, label]) => [code, label, counts.get(code)]);
  }, [jobs]);
  const metros = useMemo(() => metroCounts(preLocationFiltered).slice(0, MAX_METROS_LISTED), [preLocationFiltered]);
  // Tiers present in the feed (no empty buckets).
  const tiers = useMemo(() => {
    const present = new Set(jobs.map((j) => j.tier));
    return TIER_ORDER.filter((t) => present.has(t));
  }, [jobs]);

  return (
    <div
      role="region"
      aria-label="Filters"
      style={{
        borderRight: isMobile ? 'none' : `1px solid ${BBG.rule2}`,
        borderBottom: isMobile ? `1px solid ${BBG.rule2}` : 'none',
        overflow: 'auto',
        maxHeight: isMobile && open ? '50vh' : undefined,
        flexShrink: 0,
      }}
    >
      {isMobile && (
        <DrawerToggle open={open} onToggle={onToggleOpen} label="FILTERS" activeCount={activeFilterCount(filters)} />
      )}
      {(!isMobile || open) && (
        <>
          {/* Only reachable from a link (?new=<hours>): shown while active, one click clears it. */}
          {filters.newWithinHours ? (
            <ChipGroup title="ADDED">
              <Chip on onClick={onClearNew} label={`added in last ${filters.newWithinHours}h ×`} />
            </ChipGroup>
          ) : null}
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
          {countries.length > 1 && (
            <ChipGroup title="COUNTRY">
              {countries.map(([code, label]) => (
                <Chip key={code} on={filters.country.has(code)} onClick={() => onToggle('country', code)} label={label} />
              ))}
            </ChipGroup>
          )}
          {/* The feed only knows whether a posting states a restriction; it
              can't say a role sponsors. Label exactly that. */}
          <ChipGroup title="VISA / CITIZENSHIP">
            <Chip on={filters.visa === true} onClick={() => onVisa(true)} label="no restriction stated" />
            <Chip on={filters.visa === false} onClick={() => onVisa(false)} label="restriction stated" />
          </ChipGroup>
          <ChipGroup title="COMPANY TIER">
            {tiers.map((t) => (
              <Chip key={t} on={filters.tier.has(t)} onClick={() => onToggle('tier', t)} label={TIER_LABEL[t]} />
            ))}
          </ChipGroup>
          <CountedList
            id="location-label"
            title="LOCATION · metros"
            counts={metros}
            selected={filters.metro}
            onToggle={(m) => onToggle('metro', m)}
            isMobile={isMobile}
            noun="job"
          />
          <HiringNow jobs={preCompanyFiltered} selected={filters.company} onToggle={(co) => onToggle('company', co)} isMobile={isMobile} />
          {/* Opt-in near misses (jobs-extended.json). Counts appear once the tier has loaded; a row is shown only when every one of its reasons is on. */}
          <ChipGroup title="WIDEN SCOPE">
            {NEAR_MISS_REASONS.map((r) => {
              const n = nearMissCounts.get(r);
              const label = extended.status === 'ready' ? `${NEAR_MISS_INFO[r].label} (${n})` : NEAR_MISS_INFO[r].label;
              return <Chip key={r} on={filters.include.has(r)} onClick={() => onToggle('include', r)} label={label} />;
            })}
            {extended.status === 'loading' && <span style={{ color: BBG.dim, fontSize: 11, alignSelf: 'center' }}>loading…</span>}
            {extended.status === 'error' && <span style={{ color: BBG.warn, fontSize: 11, alignSelf: 'center' }}>near misses unavailable</span>}
          </ChipGroup>
        </>
      )}
    </div>
  );
}

function HiringNow({ jobs, selected, onToggle, isMobile }) {
  const counts = useMemo(() => companyCounts(jobs), [jobs]);
  return <CountedList id="hiring-now-label" title="HIRING NOW · companies" counts={counts} selected={selected} onToggle={onToggle} isMobile={isMobile} noun="job" />;
}

/** A scrollable list of [value, count] rows that doubles as a multi-select facet (HIRING NOW, LOCATION). */
function CountedList({ id, title, counts, selected, onToggle, isMobile, noun }) {
  return (
    <div role="group" aria-labelledby={id} style={{ padding: '12px 14px', borderTop: `1px solid ${BBG.rule}` }}>
      <div style={{ ...sectionLabel, display: 'flex', justifyContent: 'space-between' }}>
        <span id={id}>{title}</span>
        <span style={{ color: BBG.acc }}>{counts.length}</span>
      </div>
      <div style={{ maxHeight: 220, overflowY: 'auto' }}>
        {counts.map(([co, n]) => {
          const active = selected.has(co);
          return (
            <button
              key={co}
              type="button"
              aria-pressed={active}
              aria-label={`${co}, ${n} ${noun}${n === 1 ? '' : 's'}`}
              title={active ? `clear filter: ${co}` : `filter to ${co}`}
              onClick={() => onToggle(co)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%',
                fontSize: 11, padding: '1px 4px', cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                minHeight: isMobile ? MIN_TARGET + 8 : MIN_TARGET,
                border: 'none',
                background: active ? BBG.panel2 : 'transparent',
                borderLeft: `2px solid ${active ? BBG.acc : 'transparent'}`,
              }}
            >
              <span style={{ color: active ? BBG.acc : BBG.ink }}>{co}</span>
              <span style={{ color: BBG.acc }}>{n}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
